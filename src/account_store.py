"""GitHub OAuth and Gist-backed watchlist storage."""

from __future__ import annotations

import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import requests


class AccountStoreError(Exception):
    """An authentication or persistent watchlist operation failed."""


class GitHubGistAccountStore:
    API_URL = "https://api.github.com"
    OAUTH_URL = "https://github.com"
    GIST_DESCRIPTION = "CineMatch watchlist"
    WATCHLIST_FILENAME = "cinematch_watchlist.json"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        if not self.client_id or not self.client_secret:
            raise AccountStoreError("GitHub OAuth client ID and secret are required.")

    def create_github_oauth_request(self, redirect_url: str, state: str) -> str:
        normalized_redirect = redirect_url.strip()
        parsed_redirect = urlparse(normalized_redirect)
        local_http = parsed_redirect.scheme == "http" and parsed_redirect.hostname in {
            "localhost",
            "127.0.0.1",
        }
        if (
            (parsed_redirect.scheme != "https" and not local_http)
            or not parsed_redirect.netloc
            or parsed_redirect.username
            or parsed_redirect.password
            or parsed_redirect.query
            or parsed_redirect.fragment
        ):
            raise AccountStoreError("GitHub redirect URL must be a valid app HTTPS URL.")
        if not state:
            raise AccountStoreError("GitHub sign-in state is missing.")

        return (
            f"{self.OAUTH_URL}/login/oauth/authorize?"
            + urlencode(
                {
                    "client_id": self.client_id,
                    "redirect_uri": normalized_redirect,
                    "scope": "gist",
                    "state": state,
                }
            )
        )

    @staticmethod
    def validate_github_oauth_state(
        returned_state: str,
        expected_state: str,
        browser_state: str,
        expires_at: int,
    ) -> None:
        if (
            not returned_state
            or not browser_state
            or (expires_at and expires_at <= int(time.time()))
            or (
                expected_state
                and not hmac.compare_digest(returned_state, expected_state)
            )
            or not hmac.compare_digest(returned_state, browser_state)
        ):
            raise AccountStoreError("GitHub sign-in state is invalid or expired.")

    def exchange_github_oauth_code(
        self,
        auth_code: str,
        state: str,
        redirect_url: str,
    ) -> dict[str, Any]:
        if not auth_code or not state:
            raise AccountStoreError("GitHub sign-in could not verify this browser session.")
        payload = self._request(
            "POST",
            f"{self.OAUTH_URL}/login/oauth/access_token",
            form={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": auth_code,
                "redirect_uri": redirect_url,
                "state": state,
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            message = payload.get("error_description") if isinstance(payload, dict) else None
            raise AccountStoreError(str(message or "GitHub could not issue an access token."))
        scopes = {
            scope.strip()
            for scope in str(payload.get("scope") or "").split(",")
            if scope.strip()
        }
        if "gist" not in scopes:
            raise AccountStoreError("GitHub sign-in must include the Gist permission.")
        user = self._request(
            "GET",
            f"{self.API_URL}/user",
            access_token=str(payload.get("access_token") or ""),
        )
        if not isinstance(user, dict):
            raise AccountStoreError("GitHub returned an invalid account profile.")
        return self._make_session(payload, user)

    def refresh_session(self, session: dict[str, Any]) -> dict[str, Any]:
        refresh_token = str(session.get("refresh_token") or "")
        if not refresh_token:
            raise AccountStoreError("Your GitHub session expired. Please sign in again.")
        payload = self._request(
            "POST",
            f"{self.OAUTH_URL}/login/oauth/access_token",
            form={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            message = payload.get("error_description") if isinstance(payload, dict) else None
            raise AccountStoreError(str(message or "GitHub could not refresh this session."))
        return self._make_session(payload, session)

    @staticmethod
    def _make_session(
        payload: dict[str, Any],
        user: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(user, dict):
            raise AccountStoreError("GitHub returned an incomplete account session.")
        access_token = str(payload.get("access_token") or "")
        user_id = str(user.get("id") or user.get("user_id") or "")
        login = str(user.get("login") or "")
        if not access_token or not user_id or not login:
            raise AccountStoreError("GitHub returned an incomplete account session.")
        expires_in = payload.get("expires_in")
        try:
            expires_at = int(time.time()) + int(expires_in) if expires_in else 0
        except (TypeError, ValueError) as error:
            raise AccountStoreError("GitHub returned an invalid session expiry.") from error
        return {
            "access_token": access_token,
            "refresh_token": str(
                payload.get("refresh_token") or user.get("refresh_token") or ""
            ),
            "expires_at": expires_at,
            "user_id": user_id,
            "login": login,
        }

    def _request(
        self,
        method: str,
        url: str,
        *,
        access_token: str | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        form: dict[str, str] | None = None,
    ) -> Any:
        headers = {
            "Accept": (
                "application/json"
                if url.startswith(f"{self.OAUTH_URL}/login/oauth/")
                else "application/vnd.github+json"
            ),
        }
        if url.startswith(self.API_URL):
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        elif form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=body,
                data=form,
                timeout=12,
            )
        except requests.RequestException as error:
            raise AccountStoreError("Could not reach GitHub.") from error

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                details = response.json()
            except ValueError:
                details = {}
            message = details.get("message") if isinstance(details, dict) else None
            if not message:
                message = f"GitHub request failed (HTTP {response.status_code})."
            raise AccountStoreError(str(message)) from error

        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise AccountStoreError("GitHub returned an invalid response.") from error

    @staticmethod
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

    def _find_watchlist_gist(self, session: dict[str, Any]) -> dict[str, Any] | None:
        if session.get("gist_id"):
            return {"id": str(session["gist_id"])}

        page = 1
        while True:
            gists = self._request(
                "GET",
                f"{self.API_URL}/gists",
                access_token=session["access_token"],
                params={"per_page": "100", "page": str(page)},
            )
            if not isinstance(gists, list):
                raise AccountStoreError("GitHub returned an invalid Gist list.")
            for gist in gists:
                if not isinstance(gist, dict):
                    continue
                files = gist.get("files")
                if (
                    gist.get("description") == self.GIST_DESCRIPTION
                    and isinstance(files, dict)
                    and self.WATCHLIST_FILENAME in files
                    and gist.get("id")
                ):
                    session["gist_id"] = str(gist["id"])
                    return gist
            if len(gists) < 100:
                return None
            page += 1

    def _read_watchlist(
        self,
        session: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        gist = self._find_watchlist_gist(session)
        if gist is None:
            return None, []
        gist_id = str(gist.get("id") or "")
        if not gist_id:
            raise AccountStoreError("GitHub returned an invalid watchlist Gist.")
        details = self._request(
            "GET",
            f"{self.API_URL}/gists/{gist_id}",
            access_token=session["access_token"],
        )
        files = details.get("files") if isinstance(details, dict) else None
        watchlist_file = files.get(self.WATCHLIST_FILENAME) if isinstance(files, dict) else None
        content = watchlist_file.get("content") if isinstance(watchlist_file, dict) else None
        if not isinstance(content, str):
            raise AccountStoreError("GitHub did not return the saved watchlist contents.")
        try:
            document = json.loads(content)
        except json.JSONDecodeError as error:
            raise AccountStoreError("The saved watchlist contains invalid JSON.") from error
        movies = document.get("movies") if isinstance(document, dict) else None
        if not isinstance(movies, list) or not all(isinstance(movie, dict) for movie in movies):
            raise AccountStoreError("The saved watchlist has an invalid format.")
        return gist, movies

    def _write_watchlist(
        self,
        session: dict[str, Any],
        gist: dict[str, Any] | None,
        movies: list[dict[str, Any]],
    ) -> None:
        content = json.dumps(
            {"version": 1, "movies": movies},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        body = {
            "description": self.GIST_DESCRIPTION,
            "public": False,
            "files": {self.WATCHLIST_FILENAME: {"content": content}},
        }
        if gist is None:
            result = self._request(
                "POST",
                f"{self.API_URL}/gists",
                access_token=session["access_token"],
                body=body,
            )
            gist_id = result.get("id") if isinstance(result, dict) else None
            if not gist_id:
                raise AccountStoreError("GitHub did not return the new watchlist Gist.")
            session["gist_id"] = str(gist_id)
        else:
            gist_id = str(gist.get("id") or session.get("gist_id") or "")
            if not gist_id:
                raise AccountStoreError("GitHub returned an invalid watchlist Gist.")
            self._request(
                "PATCH",
                f"{self.API_URL}/gists/{gist_id}",
                access_token=session["access_token"],
                body=body,
            )

    def get_watchlist(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        _, movies = self._read_watchlist(session)
        return movies

    def save_movie(self, session: dict[str, Any], movie: dict[str, Any]) -> None:
        if not str(movie.get("title") or "").strip():
            raise AccountStoreError("A saved movie must have a title.")
        gist, movies = self._read_watchlist(session)
        movie_id = self.movie_id(movie)
        for index, saved in enumerate(movies):
            if self.movie_id(saved) == movie_id:
                movies[index] = movie
                break
        else:
            movies.append(movie)
        self._write_watchlist(session, gist, movies)

    def remove_movie(self, session: dict[str, Any], movie: dict[str, Any]) -> None:
        gist, movies = self._read_watchlist(session)
        movie_id = self.movie_id(movie)
        updated_movies = [saved for saved in movies if self.movie_id(saved) != movie_id]
        if updated_movies != movies and gist is not None:
            self._write_watchlist(session, gist, updated_movies)

    def clear_watchlist(self, session: dict[str, Any]) -> None:
        gist, _ = self._read_watchlist(session)
        if gist is not None:
            self._write_watchlist(session, gist, [])
