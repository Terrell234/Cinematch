"""Load the movie catalog and provide content-based recommendations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "movies.csv"
TEXT_COLUMNS = ("genres", "director", "cast", "moods", "overview", "keywords")
REQUIRED_COLUMNS = ("id", "title", "year", "genres", "director", "cast", "rating", "votes", "runtime")


@st.cache_data(show_spinner=False)
def load_movie_data() -> pd.DataFrame:
    """Read and normalize the bundled movie catalog."""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Movie catalog not found at {DATA_PATH}. Run `python build_dataset.py` first."
        )

    frame = pd.read_csv(DATA_PATH)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Movie catalog is missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Movie catalog contains no movies.")

    for column in TEXT_COLUMNS:
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)

    for column in ("tagline", "poster_url", "backdrop_url", "trailer_url", "box_office"):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)

    for column in ("year", "rating", "votes", "runtime"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["title", "year", "rating", "runtime"])
    frame["title"] = frame["title"].astype(str)
    return frame.reset_index(drop=True)


def get_recommender() -> "MovieRecommender":
    """Build the recommender from the current catalog."""
    return MovieRecommender(load_movie_data())


def add_movie_to_dataset(movie: dict[str, Any]) -> bool:
    """Append one movie to the local catalog; return False for duplicates."""
    frame = load_movie_data().copy()
    title = str(movie.get("title", "")).strip()
    if not title:
        raise ValueError("Cannot add a movie without a title.")
    if frame["title"].str.casefold().eq(title.casefold()).any():
        return False

    row = {column: "" for column in frame.columns}
    row.update(movie)
    row["title"] = title
    row["id"] = int(pd.to_numeric(frame["id"], errors="coerce").max() or 0) + 1
    row.setdefault("year", 0)
    row.setdefault("rating", 0)
    row.setdefault("votes", 0)
    row.setdefault("runtime", 0)

    updated = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    updated.to_csv(DATA_PATH, index=False)
    load_movie_data.clear()
    return True


class MovieRecommender:
    """TF-IDF/cosine-similarity recommender over movie metadata."""

    def __init__(self, movies: pd.DataFrame):
        self.movies = movies.reset_index(drop=True).copy()
        documents = self.movies.apply(
            lambda row: " ".join(str(row.get(column, "")) for column in TEXT_COLUMNS),
            axis=1,
        )
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(documents)
        self.similarity = cosine_similarity(self.matrix)
        self._title_indices = {
            str(title).casefold(): index for index, title in enumerate(self.movies["title"])
        }

    @staticmethod
    def _split(value: Any) -> set[str]:
        return {part.strip() for part in str(value or "").split(",") if part.strip()}

    def get_all_genres(self) -> list[str]:
        return sorted({tag for value in self.movies["genres"] for tag in self._split(value)})

    def get_all_moods(self) -> list[str]:
        return sorted({tag for value in self.movies["moods"] for tag in self._split(value)})

    def get_movie_by_title(self, title: str) -> dict[str, Any] | None:
        index = self._title_indices.get(str(title).casefold())
        return self.movies.iloc[index].to_dict() if index is not None else None

    def _eligible(
        self,
        *,
        excluded_titles: set[str] | None = None,
        genre_filter: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        max_runtime: int | None = None,
    ) -> list[int]:
        excluded = {title.casefold() for title in (excluded_titles or set())}
        genres = set(genre_filter or [])
        eligible = []
        for index, row in self.movies.iterrows():
            if str(row["title"]).casefold() in excluded:
                continue
            if float(row["rating"]) < min_rating:
                continue
            if year_range and not (year_range[0] <= int(row["year"]) <= year_range[1]):
                continue
            if max_runtime and float(row["runtime"]) > max_runtime:
                continue
            if genres and not genres.intersection(self._split(row["genres"])):
                continue
            eligible.append(index)
        return eligible

    def _format_results(self, scores: list[tuple[int, float]], top_n: int) -> list[dict[str, Any]]:
        results = []
        for index, score in scores[:top_n]:
            movie = self.movies.iloc[index].to_dict()
            movie["match_percentage"] = round(max(0.0, min(100.0, score * 100)), 1)
            results.append(movie)
        return results

    def recommend_similar(
        self,
        title: str,
        top_n: int = 6,
        genre_filter: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        max_runtime: int | None = None,
    ) -> list[dict[str, Any]]:
        seed_index = self._title_indices.get(str(title).casefold())
        if seed_index is None:
            return []
        eligible = self._eligible(
            excluded_titles={title},
            genre_filter=genre_filter,
            min_rating=min_rating,
            year_range=year_range,
            max_runtime=max_runtime,
        )
        scores = sorted(
            ((index, float(self.similarity[seed_index, index])) for index in eligible),
            key=lambda item: item[1],
            reverse=True,
        )
        seed = self.movies.iloc[seed_index]
        results = self._format_results(scores, top_n)
        for result in results:
            matching = next(
                (self.movies.iloc[index] for index, _ in scores if self.movies.iloc[index]["title"] == result["title"]),
                None,
            )
            if matching is not None:
                shared_genres = self._split(seed["genres"]) & self._split(matching["genres"])
                shared_moods = self._split(seed["moods"]) & self._split(matching["moods"])
                reasons = []
                if shared_genres:
                    reasons.append(f"Shared {', '.join(sorted(shared_genres)[:2])} themes")
                if seed["director"] and seed["director"] == matching["director"]:
                    reasons.append(f"Directed by {seed['director']}")
                if shared_moods:
                    reasons.append(f"{', '.join(sorted(shared_moods)[:2])} vibes")
                result["match_reasons"] = reasons
        return results

    def recommend_cinema_blend(
        self,
        titles: list[str],
        top_n: int = 6,
        genre_filter: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        max_runtime: int | None = None,
    ) -> list[dict[str, Any]]:
        indices = [self._title_indices[t.casefold()] for t in titles if t.casefold() in self._title_indices]
        if not indices:
            return []
        centroid = np.asarray(self.matrix[indices].mean(axis=0))
        scores = []
        for index in self._eligible(
            excluded_titles=set(titles),
            genre_filter=genre_filter,
            min_rating=min_rating,
            year_range=year_range,
            max_runtime=max_runtime,
        ):
            score = float(cosine_similarity(centroid, self.matrix[index]).ravel()[0])
            scores.append((index, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return self._format_results(scores, top_n)

    def recommend_by_mood_and_vibes(
        self,
        selected_moods: list[str],
        preferred_genres: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        max_runtime: int | None = None,
        top_n: int = 6,
    ) -> list[dict[str, Any]]:
        selected = {mood.casefold() for mood in selected_moods}
        scores = []
        for index in self._eligible(
            genre_filter=preferred_genres,
            min_rating=min_rating,
            year_range=year_range,
            max_runtime=max_runtime,
        ):
            moods = {mood.casefold() for mood in self._split(self.movies.iloc[index]["moods"])}
            overlap = len(selected & moods) / max(1, len(selected))
            rating_boost = float(self.movies.iloc[index]["rating"]) / 10
            scores.append((index, overlap * 0.8 + rating_boost * 0.2))
        scores.sort(key=lambda item: item[1], reverse=True)
        return self._format_results(scores, top_n)

    def recommend_for_watchlist(self, titles: list[str], top_n: int = 6) -> list[dict[str, Any]]:
        indices = [self._title_indices[t.casefold()] for t in titles if t.casefold() in self._title_indices]
        if not indices:
            return []
        centroid = np.asarray(self.matrix[indices].mean(axis=0))
        scores = []
        for index in self._eligible(excluded_titles=set(titles)):
            scores.append((index, float(cosine_similarity(centroid, self.matrix[index]).ravel()[0])))
        scores.sort(key=lambda item: item[1], reverse=True)
        return self._format_results(scores, top_n)
