"""Load the movie catalog and provide content-based recommendations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "movies.csv"
TEXT_COLUMNS = (
    "title",
    "genres",
    "director",
    "cast",
    "moods",
    "tagline",
    "overview",
    "keywords",
    "certification",
)
REQUIRED_COLUMNS = ("id", "title", "year", "genres", "director", "cast", "rating", "votes", "runtime")
PROMPT_EXPANSIONS = {
    "family friendly": "children kids animation heartwarming",
    "family-friendly": "children kids animation heartwarming",
    "female lead": "female protagonist heroine woman female gaze female prisoners",
    "strong female lead": "female protagonist heroine woman female gaze female prisoners",
    "funny": "comedy humorous hilarious witty",
    "hilarious": "comedy humorous funny witty",
    "scary": "horror frightening terrifying disturbing",
    "space": "science fiction sci-fi space travel astronaut planet cosmic",
    "psychological": "mind-bending paranoia identity surreal",
    "grief": "loss mourning trauma healing recovery",
    "healing": "grief loss recovery resilience hope",
    "inspiring": "hope resilience triumph uplifting",
}
PROMPT_GENRE_ALIASES = {
    "Action": ("action", "action-packed"),
    "Adventure": ("adventure",),
    "Animation": ("animation", "animated", "cartoon"),
    "Comedy": ("comedy", "funny", "humorous", "hilarious"),
    "Crime": ("crime", "criminal"),
    "Drama": ("drama",),
    "Family": (
        "family film",
        "family movie",
        "family comedy",
        "family friendly",
        "family-friendly",
        "kids",
        "kids movie",
        "children's movie",
        "children's film",
    ),
    "Fantasy": ("fantasy", "magical"),
    "History": ("history", "historical"),
    "Horror": ("horror", "scary", "frightening", "terrifying"),
    "Mystery": ("mystery", "detective", "whodunit"),
    "Romance": ("romance", "romantic", "love story"),
    "Sci-Fi": ("sci-fi", "sci fi", "science fiction", "space", "space travel"),
    "Thriller": ("thriller", "suspense", "suspenseful"),
    "War": ("war",),
    "Western": ("western",),
}


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

    for column in (
        "tagline",
        "poster_url",
        "backdrop_url",
        "trailer_url",
        "box_office",
        "certification",
        "status",
        "original_language",
    ):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)

    for column in ("year", "rating", "votes", "runtime"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("budget", "revenue"):
        if column not in frame:
            frame[column] = 0
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    frame = frame.dropna(subset=["title", "year", "rating", "runtime"])
    frame["title"] = frame["title"].astype(str)
    return frame.reset_index(drop=True)


def get_recommender() -> "MovieRecommender":
    """Build the recommender from the current catalog."""
    return MovieRecommender(load_movie_data())


def add_movie_to_dataset(movie: dict[str, Any]) -> bool:
    """Append one movie to the local catalog; return False for duplicates."""
    return add_movies_to_dataset([movie]) > 0


def add_movies_to_dataset(movies: list[dict[str, Any]]) -> int:
    """Append unique titled movies in one write and return the number added."""
    frame = load_movie_data().copy()
    existing_titles = set(frame["title"].str.casefold())
    next_id = int(pd.to_numeric(frame["id"], errors="coerce").max() or 0) + 1
    rows = []

    for movie in movies:
        title = str(movie.get("title", "")).strip()
        if not title:
            raise ValueError("Cannot add a movie without a title.")
        if title.casefold() in existing_titles:
            continue

        row = {column: "" for column in frame.columns}
        row.update(movie)
        row["id"] = next_id
        row["title"] = title
        rows.append(row)
        existing_titles.add(title.casefold())
        next_id += 1

    if not rows:
        return 0

    updated = pd.concat([frame, pd.DataFrame(rows)], ignore_index=True)
    updated.to_csv(DATA_PATH, index=False)
    load_movie_data.clear()
    return len(rows)


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
        min_runtime: int | None = None,
        min_votes: int = 0,
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
            if min_runtime is not None and float(row["runtime"]) < min_runtime:
                continue
            if max_runtime and float(row["runtime"]) > max_runtime:
                continue
            if int(row["votes"]) < min_votes:
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
        min_runtime: int | None = None,
        max_runtime: int | None = None,
        min_votes: int = 0,
    ) -> list[dict[str, Any]]:
        seed_index = self._title_indices.get(str(title).casefold())
        if seed_index is None:
            return []
        eligible = self._eligible(
            excluded_titles={title},
            genre_filter=genre_filter,
            min_rating=min_rating,
            year_range=year_range,
            min_runtime=min_runtime,
            max_runtime=max_runtime,
            min_votes=min_votes,
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

    def recommend_for_prompt(
        self,
        prompt: str,
        top_n: int = 12,
        genre_filter: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        max_runtime: int | None = None,
        min_relevance: float = 0,
        min_runtime: int | None = None,
        min_votes: int = 0,
    ) -> list[dict[str, Any]]:
        """Recommend catalog movies whose metadata best matches a free-text prompt."""
        query = str(prompt or "").strip()
        if not query:
            return []

        mentioned_titles = []
        for title in self._title_indices:
            title_pattern = re.escape(title)
            if query.casefold() == title or re.search(
                rf"\b(?:like|similar to|related to|inspired by|based on|after|if i liked)\s+"
                rf"{title_pattern}(?!\w)",
                query,
                flags=re.IGNORECASE,
            ):
                mentioned_titles.append(title)
        if mentioned_titles:
            seed_title = max(mentioned_titles, key=len)
            results = self.recommend_similar(
                title=seed_title,
                top_n=top_n,
                genre_filter=genre_filter,
                min_rating=min_rating,
                year_range=year_range,
                min_runtime=min_runtime,
                max_runtime=max_runtime,
                min_votes=min_votes,
            )
            return [
                movie
                for movie in results
                if movie["match_percentage"] >= min_relevance
            ]

        available_genres = {genre.casefold(): genre for genre in self.get_all_genres()}
        prompt_genres = {
            available_genres[genre.casefold()]
            for genre, aliases in PROMPT_GENRE_ALIASES.items()
            if genre.casefold() in available_genres
            and any(
                re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", query, flags=re.IGNORECASE)
                for alias in aliases
            )
        }
        expanded_terms = [
            expansion
            for phrase, expansion in PROMPT_EXPANSIONS.items()
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", query, flags=re.IGNORECASE)
        ]
        expanded_query = " ".join([query, *expanded_terms])
        query_vector = self.vectorizer.transform([expanded_query])
        if not query_vector.nnz:
            return []

        eligible = self._eligible(
            genre_filter=genre_filter,
            min_rating=min_rating,
            year_range=year_range,
            min_runtime=min_runtime,
            max_runtime=max_runtime,
            min_votes=min_votes,
        )
        if prompt_genres:
            eligible = [
                index
                for index in eligible
                if prompt_genres.issubset(self._split(self.movies.iloc[index]["genres"]))
            ]

        query_terms = set(self.vectorizer.build_analyzer()(expanded_query))
        scores = [
            (index, float(cosine_similarity(query_vector, self.matrix[index]).ravel()[0]))
            for index in eligible
        ]
        scores = [
            item
            for item in scores
            if item[1] > 0 and item[1] * 100 >= min_relevance
        ]
        scores.sort(
            key=lambda item: (
                item[1],
                float(self.movies.iloc[item[0]]["rating"]),
                int(self.movies.iloc[item[0]]["votes"]),
            ),
            reverse=True,
        )

        results = self._format_results(scores, top_n)
        for result, (index, _) in zip(results, scores):
            movie_terms = set(
                self.vectorizer.build_analyzer()(
                    " ".join(
                        str(self.movies.iloc[index].get(column, ""))
                        for column in TEXT_COLUMNS
                    )
                )
            )
            shared_terms = sorted(query_terms & movie_terms)
            result["match_reasons"] = (
                [f"Related themes: {', '.join(shared_terms[:3])}"]
                if shared_terms
                else []
            )
        return results

    def recommend_cinema_blend(
        self,
        titles: list[str],
        top_n: int = 6,
        genre_filter: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        max_runtime: int | None = None,
        min_runtime: int | None = None,
        min_votes: int = 0,
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
            min_runtime=min_runtime,
            max_runtime=max_runtime,
            min_votes=min_votes,
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
        min_runtime: int | None = None,
        min_votes: int = 0,
    ) -> list[dict[str, Any]]:
        selected = {mood.casefold() for mood in selected_moods}
        scores = []
        for index in self._eligible(
            genre_filter=preferred_genres,
            min_rating=min_rating,
            year_range=year_range,
            min_runtime=min_runtime,
            max_runtime=max_runtime,
            min_votes=min_votes,
        ):
            moods = {mood.casefold() for mood in self._split(self.movies.iloc[index]["moods"])}
            overlap = len(selected & moods) / max(1, len(selected))
            rating_boost = float(self.movies.iloc[index]["rating"]) / 10
            scores.append((index, overlap * 0.8 + rating_boost * 0.2))
        scores.sort(key=lambda item: item[1], reverse=True)
        return self._format_results(scores, top_n)

    def recommend_for_watchlist(
        self,
        titles: list[str],
        top_n: int = 6,
        *,
        genre_filter: list[str] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
        min_runtime: int | None = None,
        max_runtime: int | None = None,
        min_votes: int = 0,
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
            min_runtime=min_runtime,
            max_runtime=max_runtime,
            min_votes=min_votes,
        ):
            scores.append((index, float(cosine_similarity(centroid, self.matrix[index]).ravel()[0])))
        scores.sort(key=lambda item: item[1], reverse=True)
        return self._format_results(scores, top_n)
