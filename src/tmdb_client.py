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
        878: "Sci-Fi",
        9648: "Mystery",
        10402: "Music",
        10749: "Romance",
        10751: "Family",
        10752: "War",
        10770: "TV Movie",
    }

    def __init__(self, api_key_or_token: str = ""):
        self.credential = (
            api_key_or_token
            or os.getenv("TMDB_API_KEY", "")
            or os.getenv("TMDB_API_TOKEN", "")
        ).strip()
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
        runtime_range: tuple[int, int] | None = None,
        min_votes: int = 0,
    ) -> list[dict[str, Any]]:
        """Filter TMDB list results by genre, score, year, runtime, and vote count."""
        filtered = []
        for movie in movies:
            if float(movie.get("vote_average") or 0) < min_rating:
                continue
            if int(movie.get("vote_count") or 0) < min_votes:
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
            if runtime_range is not None:
                runtime = movie.get("runtime")
                if runtime is None or not runtime_range[0] <= int(runtime) <= runtime_range[1]:
                    continue
            filtered.append(movie)
        return filtered

    @staticmethod
    def filter_movies_with_posters(movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep TMDB results that include a poster image path."""
        return [
            movie
            for movie in movies
            if str(movie.get("poster_path") or "").strip()
        ]

    def get_trending_movies(self, time_window: str = "week") -> list[dict[str, Any]]:
        return self._get(f"trending/movie/{time_window}").get("results", [])

    def get_now_playing(self, page: int = 1) -> list[dict[str, Any]]:
        return self._get("movie/now_playing", {"page": page}).get("results", [])

    def get_top_rated(self, page: int = 1) -> list[dict[str, Any]]:
        return self._get("movie/top_rated", {"page": page}).get("results", [])

    def get_popular_movies(self, page: int = 1) -> list[dict[str, Any]]:
        return self._get(
            "discover/movie",
            {
                "page": page,
                "sort_by": "popularity.desc",
                "include_adult": "false",
                "include_video": "false",
                "vote_count.gte": 50,
            },
        ).get("results", [])

    def get_movie_recommendations(self, tmdb_id: int | str, page: int = 1) -> list[dict[str, Any]]:
        return self._get(f"movie/{tmdb_id}/recommendations", {"page": page}).get("results", [])

    def search_movies(self, query: str, year: int | None = None) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        params: dict[str, Any] = {"query": query, "include_adult": "false"}
        if year is not None:
            params["year"] = year
        return self._get("search/movie", params).get("results", [])

    def get_catalog_poster(self, title: str, year: int) -> dict[str, Any] | None:
        """Find a poster for an exact catalog title/year, retrying broad search if needed."""
        normalized_title = str(title or "").strip()
        if not normalized_title or not self.is_configured:
            return None

        catalog_movie = [{"title": normalized_title, "year": int(year)}]
        title_year = (normalized_title.casefold(), int(year))
        year_results = self.search_movies(normalized_title, year=int(year))
        matched, _ = self.match_catalog_search_posters(catalog_movie, year_results)
        poster = matched.get(title_year)
        if poster and poster.get("poster_url"):
            return poster

        all_results = self.search_movies(normalized_title)
        matched, _ = self.match_catalog_search_posters(catalog_movie, all_results)
        poster = matched.get(title_year)
        return poster if poster and poster.get("poster_url") else None

    def match_catalog_search_posters(
        self,
        catalog_movies: list[dict[str, Any]],
        tmdb_movies: list[dict[str, Any]],
    ) -> tuple[dict[tuple[str, int], dict[str, Any]], list[dict[str, Any]]]:
        """Match TMDB poster art to catalog titles only when title and year agree."""
        catalog_keys = {
            (str(movie["title"]).casefold(), int(movie["year"]))
            for movie in catalog_movies
        }
        matched_posters = {}
        unmatched_movies = []
        for item in tmdb_movies:
            movie = self.format_tmdb_movie(item)
            movie["tmdb_id"] = item.get("id")
            title_year = (movie["title"].casefold(), movie["year"])
            if title_year in catalog_keys:
                matched_posters[title_year] = movie
            elif movie["poster_url"]:
                movie["id"] = item.get("id")
                unmatched_movies.append(movie)
        return matched_posters, unmatched_movies

    def get_movie_details(self, tmdb_id: int | str) -> dict[str, Any]:
        return self._get(
            f"movie/{tmdb_id}",
            {"append_to_response": "credits,videos,keywords,release_dates"},
        )

    @staticmethod
    def get_trailer_url(item: dict[str, Any]) -> str:
        """Return the official YouTube trailer URL from TMDB video metadata."""
        videos = (item.get("videos") or {}).get("results", [])
        trailers = [
            video
            for video in videos
            if video.get("site") == "YouTube"
            and video.get("type") == "Trailer"
            and video.get("key")
        ]
        if not trailers:
            return ""
        trailer = next((video for video in trailers if video.get("official")), trailers[0])
        return f"https://www.youtube.com/watch?v={trailer['key']}"

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
        keyword_data = item.get("keywords") or {}
        if isinstance(keyword_data, dict):
            keyword_data = keyword_data.get("keywords") or keyword_data.get("results") or []
        keywords = [
            keyword.get("name", "")
            for keyword in keyword_data
            if isinstance(keyword, dict) and keyword.get("name")
        ]
        release_dates = item.get("release_dates") or {}
        release_countries = release_dates.get("results", []) if isinstance(release_dates, dict) else []
        release_countries = sorted(
            release_countries,
            key=lambda country: country.get("iso_3166_1") != "US",
        )
        certification = next(
            (
                str(release.get("certification") or "").strip()
                for country in release_countries
                for release in country.get("release_dates", [])
                if str(release.get("certification") or "").strip()
            ),
            "",
        )
        trailer = self.get_trailer_url(item)
        poster = item.get("poster_path")
        backdrop = item.get("backdrop_path")
        revenue = int(item.get("revenue") or 0)
        budget = int(item.get("budget") or 0)
        return {
            "title": item.get("title") or item.get("name") or "Untitled",
            "year": int(release_date[:4]) if release_date[:4].isdigit() else 0,
            "certification": certification,
            "genres": ", ".join(genre_names),
            "director": ", ".join(directors),
            "cast": ", ".join(name for name in cast if name),
            "rating": round(float(item.get("vote_average") or 0), 1),
            "votes": int(item.get("vote_count") or 0),
            "runtime": int(item.get("runtime") or 0),
            "moods": "",
            "tagline": item.get("tagline") or "",
            "overview": item.get("overview") or "",
            "keywords": ", ".join(keywords),
            "poster_url": f"{self.IMAGE_URL}/w500{poster}" if poster else "",
            "backdrop_url": f"{self.IMAGE_URL}/w1280{backdrop}" if backdrop else "",
            "trailer_url": trailer,
            "box_office": f"${revenue:,}" if revenue else "",
            "budget": budget,
            "revenue": revenue,
            "status": item.get("status") or "",
            "original_language": item.get("original_language") or "",
            "tmdb_id": item.get("id"),
        }
