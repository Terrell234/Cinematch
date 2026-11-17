"""Session-local watchlist operations."""

from __future__ import annotations

from typing import Any


def movie_id(movie: dict[str, Any]) -> str:
    tmdb_id = str(movie.get("tmdb_id") or "").strip()
    if tmdb_id and tmdb_id.casefold() not in {"nan", "none"}:
        return f"tmdb:{tmdb_id}"

    title = str(movie.get("title") or "").strip().casefold()
    try:
        year = int(movie.get("year") or 0)
    except (TypeError, ValueError):
        year = 0
    return f"catalog:{title}:{year}"


def add_movie(
    watchlist: list[dict[str, Any]],
    movie: dict[str, Any],
) -> list[dict[str, Any]]:
    target_id = movie_id(movie)
    for index, saved in enumerate(watchlist):
        if movie_id(saved) == target_id:
            return [*watchlist[:index], movie, *watchlist[index + 1 :]]
    return [*watchlist, movie]


def remove_movie(
    watchlist: list[dict[str, Any]],
    movie: dict[str, Any],
) -> list[dict[str, Any]]:
    target_id = movie_id(movie)
    return [saved for saved in watchlist if movie_id(saved) != target_id]
