"""Small TMDB API client used by the Streamlit discovery pages."""

from __future__ import annotations

import os
from typing import Any

import requests


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_URL = "https://image.tmdb.org/t/p"
    GENRE_IDS = {
        "anime": 16,
        "action": 28,
        "adventure": 12,
        "animation": 16,
        "comedy": 35,
        "crime": 80,
        "documentary": 99,
        "drama": 18,
        "family": 10751,
        "fantasy": 14,
        "history": 36,
        "horror": 27,
        "music": 10402,
        "mystery": 9648,
        "romance": 10749,
        "sci-fi": 878,
        "science fiction": 878,
        "tv movie": 10770,
        "thriller": 53,
        "war": 10752,
        "western": 37,
    }
    GENRE_NAMES = {
        12: "Adventure",
        14: "Fantasy",
        16: "Animation",
        18: "Drama",
        27: "Horror",
        28: "Action",
        35: "Comedy",
        36: "History",
        37: "Western",
        53: "Thriller",
        80: "Crime",
        99: "Documentary",
        878: "Science Fiction",
        9648: "Mystery",
        10402: "Music",
        10749: "Romance",
        10751: "Family",
        10752: "War",
        10770: "TV Movie",
    }

    def __init__(self, api_key_or_token: str = ""):
        self.credential = (api_key_or_token or os.getenv("TMDB_API_KEY", "")).strip()
        self.is_configured = bool(self.credential)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if self.credential.startswith("eyJ"):
            self.session.headers["Authorization"] = f"Bearer {self.credential}"
            self.params: dict[str, str] = {}
        else:
            self.params = {"api_key": self.credential} if self.credential else {}

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.is_configured:
            return {}
        query = {**self.params, **(params or {})}
        response = self.session.get(f"{self.BASE_URL}/{endpoint.lstrip('/')}", params=query, timeout=12)
        response.raise_for_status()
        return response.json()

    @classmethod
    def genre_ids_for_names(cls, genres: list[str]) -> set[int]:
        """Translate selected catalog genre labels to TMDB genre IDs."""
        return {
            cls.GENRE_IDS[genre.strip().casefold()]
            for genre in genres
            if genre.strip().casefold() in cls.GENRE_IDS
        }

    @staticmethod
    def filter_movie_results(
        movies: list[dict[str, Any]],
        *,
        genre_ids: set[int] | None = None,
        min_rating: float = 0,
        year_range: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter TMDB list results by genre, vote average, and release year."""
        filtered = []
        for movie in movies:
            if float(movie.get("vote_average") or 0) < min_rating:
                continue
            if genre_ids is not None:
                movie_genres = {int(genre_id) for genre_id in movie.get("genre_ids", [])}
                if not genre_ids.intersection(movie_genres):
                    continue
            if year_range is not None:
                release_date = str(movie.get("release_date") or "")
                year_text = release_date[:4]
                if not year_text.isdigit() or not year_range[0] <= int(year_text) <= year_range[1]:
                    continue
            filtered.append(movie)
        return filtered

    def get_trending_movies(self, time_window: str = "week") -> list[dict[str, Any]]:
        return self._get(f"trending/movie/{time_window}").get("results", [])

    def get_now_playing(self, page: int = 1) -> list[dict[str, Any]]:
        return self._get("movie/now_playing", {"page": page}).get("results", [])

    def get_top_rated(self, page: int = 1) -> list[dict[str, Any]]:
        return self._get("movie/top_rated", {"page": page}).get("results", [])

    def get_movie_recommendations(self, tmdb_id: int | str, page: int = 1) -> list[dict[str, Any]]:
        return self._get(f"movie/{tmdb_id}/recommendations", {"page": page}).get("results", [])

    def search_movies(self, query: str) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        return self._get("search/movie", {"query": query, "include_adult": "false"}).get("results", [])

    def get_movie_details(self, tmdb_id: int | str) -> dict[str, Any]:
        return self._get(f"movie/{tmdb_id}", {"append_to_response": "credits,videos"})

    def get_category_feed(self, category: str) -> list[dict[str, Any]]:
        if category == "new":
            return self.get_now_playing()
        if category == "popular":
            return self.get_trending_movies()
        genre_id = self.GENRE_IDS.get(category.casefold())
        if genre_id is None:
            return self.get_trending_movies()
        return self._get("discover/movie", {"with_genres": genre_id, "sort_by": "popularity.desc"}).get("results", [])

    def format_tmdb_movie(self, item: dict[str, Any]) -> dict[str, Any]:
        release_date = item.get("release_date") or ""
        genres = item.get("genres") or []
        if genres and isinstance(genres[0], dict):
            genre_names = [genre.get("name", "") for genre in genres]
        else:
            genre_names = [
                self.GENRE_NAMES[genre_id]
                for genre_id in item.get("genre_ids", [])
                if genre_id in self.GENRE_NAMES
            ]
        credits = item.get("credits") or {}
        cast = [person.get("name", "") for person in credits.get("cast", [])[:5]]
        directors = [
            person.get("name", "")
            for person in credits.get("crew", [])
            if person.get("job") == "Director"
        ]
        videos = (item.get("videos") or {}).get("results", [])
        trailer = next(
            (
                f"https://www.youtube.com/watch?v={video['key']}"
                for video in videos
                if video.get("site") == "YouTube" and video.get("type") == "Trailer"
            ),
            "",
        )
        poster = item.get("poster_path")
        backdrop = item.get("backdrop_path")
        return {
            "title": item.get("title") or item.get("name") or "Untitled",
            "year": int(release_date[:4]) if release_date[:4].isdigit() else 0,
            "genres": ", ".join(genre_names),
            "director": ", ".join(directors),
            "cast": ", ".join(name for name in cast if name),
            "rating": round(float(item.get("vote_average") or 0), 1),
            "votes": int(item.get("vote_count") or 0),
            "runtime": int(item.get("runtime") or 0),
            "moods": "",
            "tagline": item.get("tagline") or "",
            "overview": item.get("overview") or "",
            "keywords": "",
            "poster_url": f"{self.IMAGE_URL}/w500{poster}" if poster else "",
            "backdrop_url": f"{self.IMAGE_URL}/w1280{backdrop}" if backdrop else "",
            "trailer_url": trailer,
            "box_office": "",
        }
