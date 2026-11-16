"""Supabase Auth and row-level-secured watchlist storage."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse

from cryptography.fernet import Fernet, InvalidToken
import requests


class AccountStoreError(Exception):
    """An authentication or persistent watchlist operation failed."""


class SupabaseAccountStore:
    def __init__(self, project_url: str, anon_key: str):
        normalized_url = project_url.strip()
        parsed_url = urlparse(normalized_url)
        if (
            parsed_url.scheme != "https"
            or not parsed_url.netloc
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise AccountStoreError("Supabase URL must be a valid HTTPS URL.")
        if self._is_service_role_key(anon_key):
            raise AccountStoreError(
                "Use the Supabase public anon key, never the service_role key."
            )
        self.project_url = normalized_url.rstrip("/")
        self.anon_key = anon_key

    @staticmethod
    def _is_service_role_key(key: str) -> bool:
        if key.startswith("sb_secret_"):
            return True
        parts = key.split(".")
        if len(parts) != 3:
            return False
        try:
            encoded_payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(encoded_payload))
        except (binascii.Error, ValueError):
            return False
        return isinstance(claims, dict) and claims.get("role") == "service_role"

    @staticmethod
    def _oauth_cipher(state_secret: str) -> Fernet:
        if not state_secret:
            raise AccountStoreError("GitHub OAuth state secret is not configured.")
        key = base64.urlsafe_b64encode(hashlib.sha256(state_secret.encode()).digest())
        return Fernet(key)

    def create_github_oauth_request(
        self,
        redirect_url: str,
        state_secret: str,
    ) -> tuple[str, str]:
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

        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        nonce = secrets.token_urlsafe(32)
        state = self._oauth_cipher(state_secret).encrypt(
            json.dumps(
                {
                    "verifier": verifier,
                    "nonce": nonce,
                    "issued_at": int(time.time()),
                }
            ).encode()
        ).decode()
        callback_url = f"{normalized_redirect}?oauth_state={state}"
        authorization_url = (
            f"{self.project_url}/auth/v1/authorize?"
            + urlencode(
                {
                    "provider": "github",
                    "redirect_to": callback_url,
                    "code_challenge": challenge,
                    "code_challenge_method": "s256",
                }
            )
        )
        return authorization_url, nonce

    def exchange_github_oauth_code(
        self,
        auth_code: str,
        encrypted_state: str,
        browser_nonce: str,
        state_secret: str,
    ) -> dict[str, Any]:
        if not auth_code or not encrypted_state or not browser_nonce:
            raise AccountStoreError("GitHub sign-in could not verify this browser session.")
        try:
            state_bytes = self._oauth_cipher(state_secret).decrypt(
                encrypted_state.encode(),
                ttl=600,
            )
            state = json.loads(state_bytes)
        except (InvalidToken, UnicodeDecodeError, ValueError) as error:
            raise AccountStoreError("GitHub sign-in state is invalid or expired.") from error
        if not isinstance(state, dict):
            raise AccountStoreError("GitHub sign-in state is invalid.")
        try:
            issued_at = int(state["issued_at"])
            verifier = str(state["verifier"])
            state_nonce = str(state["nonce"])
        except (KeyError, TypeError, ValueError) as error:
            raise AccountStoreError("GitHub sign-in state is invalid.") from error
        if (
            time.time() - issued_at > 600
            or issued_at > time.time() + 60
            or not hmac.compare_digest(state_nonce, browser_nonce)
        ):
            raise AccountStoreError("GitHub sign-in state is invalid or expired.")

        payload = self._request(
            "POST",
            "auth/v1/token?grant_type=pkce",
            body={"auth_code": auth_code, "code_verifier": verifier},
        )
        return self._make_session(payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token or self.anon_key}",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer

        try:
            response = requests.request(
                method,
                f"{self.project_url}/{path.lstrip('/')}",
                headers=headers,
                params=params,
                json=body,
                timeout=12,
            )
        except requests.RequestException as error:
            raise AccountStoreError("Could not reach the account service.") from error

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                details = response.json()
            except ValueError:
                details = {}
            if not isinstance(details, dict):
                details = {}
            message = (
                details.get("msg")
                or details.get("message")
                or details.get("error_description")
                or details.get("error")
            )
            if not message:
                message = f"Account service request failed (HTTP {response.status_code})."
            raise AccountStoreError(str(message)) from error

        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise AccountStoreError("Account service returned an invalid response.") from error

    @staticmethod
    def _make_session(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise AccountStoreError("Account service returned an invalid session.")
        user = payload.get("user") or {}
        if not isinstance(user, dict):
            raise AccountStoreError("Account service returned an invalid user.")
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        user_id = user.get("id")
        if not access_token or not refresh_token or not user_id:
            raise AccountStoreError("Account service did not return a complete login session.")
        try:
            expires_at = int(
                payload.get("expires_at")
                or time.time() + int(payload.get("expires_in") or 3600)
            )
        except (TypeError, ValueError) as error:
            raise AccountStoreError("Account service returned an invalid session expiry.") from error
        return {
            "access_token": str(access_token),
            "refresh_token": str(refresh_token),
            "expires_at": expires_at,
            "user_id": str(user_id),
            "email": str(user.get("email") or ""),
        }

    def sign_up(self, email: str, password: str) -> dict[str, Any] | None:
        payload = self._request(
            "POST",
            "auth/v1/signup",
            body={"email": email, "password": password},
        )
        if not isinstance(payload, dict):
            raise AccountStoreError("Account service returned an invalid sign-up response.")
        return self._make_session(payload) if payload.get("access_token") else None

    def sign_in(self, email: str, password: str) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "auth/v1/token?grant_type=password",
            body={"email": email, "password": password},
        )
        return self._make_session(payload)

    def refresh_session(self, refresh_token: str) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "auth/v1/token?grant_type=refresh_token",
            body={"refresh_token": refresh_token},
        )
        return self._make_session(payload)

    def sign_out(self, access_token: str) -> None:
        self._request("POST", "auth/v1/logout", access_token=access_token)

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

    def get_watchlist(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "rest/v1/user_watchlists",
            access_token=session["access_token"],
            params={
                "select": "movie_id,movie_data",
                "user_id": f"eq.{session['user_id']}",
                "order": "created_at.asc",
            },
        )
        if not isinstance(rows, list):
            raise AccountStoreError("Account service returned an invalid watchlist.")
        movies = []
        for row in rows:
            movie = row.get("movie_data") if isinstance(row, dict) else None
            if not isinstance(movie, dict):
                raise AccountStoreError("Account service returned an invalid saved movie.")
            movies.append(movie)
        return movies

    def save_movie(self, session: dict[str, Any], movie: dict[str, Any]) -> None:
        if not str(movie.get("title") or "").strip():
            raise AccountStoreError("A saved movie must have a title.")
        self._request(
            "POST",
            "rest/v1/user_watchlists?on_conflict=user_id,movie_id",
            access_token=session["access_token"],
            body={
                "user_id": session["user_id"],
                "movie_id": self.movie_id(movie),
                "movie_data": movie,
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def remove_movie(self, session: dict[str, Any], movie: dict[str, Any]) -> None:
        self._request(
            "DELETE",
            "rest/v1/user_watchlists",
            access_token=session["access_token"],
            params={
                "user_id": f"eq.{session['user_id']}",
                "movie_id": f"eq.{self.movie_id(movie)}",
            },
            prefer="return=minimal",
        )

    def clear_watchlist(self, session: dict[str, Any]) -> None:
        self._request(
            "DELETE",
            "rest/v1/user_watchlists",
            access_token=session["access_token"],
            params={"user_id": f"eq.{session['user_id']}"},
            prefer="return=minimal",
        )
