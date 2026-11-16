"""Google OAuth and private Google Drive app-data watchlist storage."""

from __future__ import annotations

import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import requests


class AccountStoreError(Exception):
    """An authentication or persistent watchlist operation failed."""


class GoogleDriveAccountStore:
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
    API_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"
    DRIVE_APPDATA_SCOPE = "https://www.googleapis.com/auth/drive.appdata"
    WATCHLIST_FILENAME = "cinematch_watchlist.json"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        if not self.client_id or not self.client_secret:
            raise AccountStoreError("Google OAuth client ID and secret are required.")

    def create_google_oauth_request(self, redirect_url: str, state: str) -> str:
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
            raise AccountStoreError("Google redirect URL must be a valid app HTTPS URL.")
        if not state:
            raise AccountStoreError("Google sign-in state is missing.")

        return self.AUTHORIZATION_URL + "?" + urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": normalized_redirect,
                "response_type": "code",
                "scope": f"openid email profile {self.DRIVE_APPDATA_SCOPE}",
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
            }
        )

    @staticmethod
    def validate_google_oauth_state(
        returned_state: str,
        expected_state: str,
        browser_state: str,
        expires_at: int,
    ) -> None:
        if (
            not returned_state
            or not expected_state
            or not browser_state
            or expires_at <= int(time.time())
            or not hmac.compare_digest(returned_state, expected_state)
            or not hmac.compare_digest(returned_state, browser_state)
        ):
            raise AccountStoreError("Google sign-in state is invalid or expired.")

    def exchange_google_oauth_code(
        self,
        auth_code: str,
        redirect_url: str,
    ) -> dict[str, Any]:
        if not auth_code:
            raise AccountStoreError("Google sign-in did not return an authorization code.")
        payload = self._request(
            "POST",
            self.TOKEN_URL,
            form={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": auth_code,
                "redirect_uri": redirect_url,
                "grant_type": "authorization_code",
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            message = (
                payload.get("error_description")
                if isinstance(payload, dict)
                else None
            )
            raise AccountStoreError(str(message or "Google could not issue an access token."))
        user = self._request(
            "GET",
            self.USERINFO_URL,
            access_token=str(payload.get("access_token") or ""),
        )
        if not isinstance(user, dict):
            raise AccountStoreError("Google returned an invalid account profile.")
        return self._make_session(payload, user)

    def refresh_session(self, session: dict[str, Any]) -> dict[str, Any]:
        refresh_token = str(session.get("refresh_token") or "")
        if not refresh_token:
            raise AccountStoreError("Your Google session expired. Please sign in again.")
        payload = self._request(
            "POST",
            self.TOKEN_URL,
            form={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if not isinstance(payload, dict) or payload.get("error"):
            message = (
                payload.get("error_description")
                if isinstance(payload, dict)
                else None
            )
            raise AccountStoreError(str(message or "Google could not refresh this session."))
        return self._make_session(payload, session)

    @staticmethod
    def _make_session(
        payload: dict[str, Any],
        user: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(user, dict):
            raise AccountStoreError("Google returned an incomplete account session.")
        access_token = str(payload.get("access_token") or "")
        user_id = str(user.get("sub") or user.get("user_id") or "")
        email = str(user.get("email") or user.get("login") or "").strip()
        email_verified = user.get("email_verified") is True or str(
            user.get("email_verified") or ""
        ).casefold() == "true"
        if not access_token or not user_id or not email or not email_verified:
            raise AccountStoreError(
                "Google must return a verified email and complete account profile."
            )
        expires_in = payload.get("expires_in")
        try:
            expires_at = int(time.time()) + int(expires_in) if expires_in else 0
        except (TypeError, ValueError) as error:
            raise AccountStoreError("Google returned an invalid session expiry.") from error
        return {
            "access_token": access_token,
            "refresh_token": str(
                payload.get("refresh_token") or user.get("refresh_token") or ""
            ),
            "expires_at": expires_at,
            "user_id": user_id,
            "login": email,
            "email": email,
            "name": str(user.get("name") or email),
            "email_verified": True,
            "provider": "google",
            "drive_file_id": str(user.get("drive_file_id") or ""),
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
        data: str | None = None,
        content_type: str | None = None,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        elif form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data is not None:
            headers["Content-Type"] = content_type or "application/json"

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=body,
                data=form if form is not None else data,
                timeout=12,
            )
        except requests.RequestException as error:
            raise AccountStoreError("Could not reach Google.") from error

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                details = response.json()
            except ValueError:
                details = {}
            message = None
            if isinstance(details, dict):
                message = details.get("error_description")
                error_details = details.get("error")
                if isinstance(error_details, dict):
                    message = message or error_details.get("message")
            if not message:
                message = f"Google request failed (HTTP {response.status_code})."
            raise AccountStoreError(str(message)) from error

        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise AccountStoreError("Google returned an invalid response.") from error

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

    def _find_watchlist_file(
        self, session: dict[str, Any]
    ) -> dict[str, Any] | None:
        if session.get("drive_file_id"):
            return {"id": str(session["drive_file_id"])}

        page_token = ""
        while True:
            params = {
                "q": (
                    f"name = '{self.WATCHLIST_FILENAME}' and "
                    "'appDataFolder' in parents and trashed = false"
                ),
                "spaces": "appDataFolder",
                "pageSize": "100",
                "fields": "nextPageToken,files(id,name)",
            }
            if page_token:
                params["pageToken"] = page_token
            result = self._request(
                "GET",
                f"{self.API_URL}/files",
                access_token=session["access_token"],
                params=params,
            )
            files = result.get("files") if isinstance(result, dict) else None
            if not isinstance(files, list):
                raise AccountStoreError("Google returned an invalid app-data file list.")
            for file in files:
                if (
                    isinstance(file, dict)
                    and file.get("name") == self.WATCHLIST_FILENAME
                    and file.get("id")
                ):
                    session["drive_file_id"] = str(file["id"])
                    return file
            page_token = str(result.get("nextPageToken") or "")
            if not page_token:
                return None

    def _read_watchlist(
        self, session: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        file = self._find_watchlist_file(session)
        if file is None:
            return None, []
        file_id = str(file.get("id") or "")
        if not file_id:
            raise AccountStoreError("Google returned an invalid watchlist file.")
        document = self._request(
            "GET",
            f"{self.API_URL}/files/{file_id}",
            access_token=session["access_token"],
            params={"alt": "media"},
        )
        movies = document.get("movies") if isinstance(document, dict) else None
        if not isinstance(movies, list) or not all(
            isinstance(movie, dict) for movie in movies
        ):
            raise AccountStoreError("The saved watchlist has an invalid format.")
        return file, movies

    def _write_watchlist(
        self,
        session: dict[str, Any],
        file: dict[str, Any] | None,
        movies: list[dict[str, Any]],
    ) -> None:
        content = json.dumps(
            {"version": 1, "movies": movies},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        file_id = str((file or {}).get("id") or session.get("drive_file_id") or "")
        if not file_id:
            result = self._request(
                "POST",
                f"{self.API_URL}/files",
                access_token=session["access_token"],
                params={"fields": "id"},
                body={
                    "name": self.WATCHLIST_FILENAME,
                    "mimeType": "application/json",
                    "parents": ["appDataFolder"],
                },
            )
            file_id = str(result.get("id") or "") if isinstance(result, dict) else ""
            if not file_id:
                raise AccountStoreError("Google did not create the watchlist file.")
            session["drive_file_id"] = file_id

        self._request(
            "PATCH",
            f"{self.UPLOAD_URL}/files/{file_id}",
            access_token=session["access_token"],
            params={"uploadType": "media"},
            data=content,
            content_type="application/json; charset=UTF-8",
        )

    def get_watchlist(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        _, movies = self._read_watchlist(session)
        return movies

    def save_movie(self, session: dict[str, Any], movie: dict[str, Any]) -> None:
        if not str(movie.get("title") or "").strip():
            raise AccountStoreError("A saved movie must have a title.")
        file, movies = self._read_watchlist(session)
        movie_id = self.movie_id(movie)
        for index, saved in enumerate(movies):
            if self.movie_id(saved) == movie_id:
                movies[index] = movie
                break
        else:
            movies.append(movie)
        self._write_watchlist(session, file, movies)

    def remove_movie(self, session: dict[str, Any], movie: dict[str, Any]) -> None:
        file, movies = self._read_watchlist(session)
        movie_id = self.movie_id(movie)
        updated_movies = [saved for saved in movies if self.movie_id(saved) != movie_id]
        if updated_movies != movies and file is not None:
            self._write_watchlist(session, file, updated_movies)

    def clear_watchlist(self, session: dict[str, Any]) -> None:
        file, _ = self._read_watchlist(session)
        if file is not None:
            self._write_watchlist(session, file, [])
