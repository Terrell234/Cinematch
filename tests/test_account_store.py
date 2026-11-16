import json
import time
import unittest
from unittest.mock import Mock, call, patch
from urllib.parse import parse_qs, urlparse

from requests import HTTPError

from src.account_store import AccountStoreError, GoogleDriveAccountStore


class GoogleDriveAccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = GoogleDriveAccountStore("client-id", "client-secret")
        self.session = {
            "access_token": "user-access-token",
            "refresh_token": "user-refresh-token",
            "expires_at": 1_900_000_000,
            "user_id": "google-user-id",
            "login": "movie-fan@example.com",
            "email": "movie-fan@example.com",
            "name": "Movie Fan",
            "email_verified": True,
        }

    @staticmethod
    def response(payload, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.content = json.dumps(payload).encode()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    def test_oauth_request_uses_identity_and_private_drive_scopes(self):
        url = self.store.create_google_oauth_request(
            "https://cinematch.example",
            "one-time-state",
        )
        params = parse_qs(urlparse(url).query)

        self.assertEqual(urlparse(url).netloc, "accounts.google.com")
        self.assertEqual(params["client_id"], ["client-id"])
        self.assertEqual(params["redirect_uri"], ["https://cinematch.example"])
        self.assertIn("openid", params["scope"][0].split())
        self.assertIn("email", params["scope"][0].split())
        self.assertIn(self.store.DRIVE_APPDATA_SCOPE, params["scope"][0].split())
        self.assertEqual(params["state"], ["one-time-state"])
        self.assertEqual(params["access_type"], ["offline"])

    def test_oauth_request_rejects_non_https_redirect(self):
        with self.assertRaisesRegex(AccountStoreError, "HTTPS"):
            self.store.create_google_oauth_request(
                "http://cinematch.example",
                "one-time-state",
            )

    def test_oauth_state_requires_matching_browser_and_unexpired_state(self):
        expires_at = int(time.time()) + 600

        GoogleDriveAccountStore.validate_google_oauth_state(
            "state-123",
            "state-123",
            "state-123",
            expires_at,
        )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GoogleDriveAccountStore.validate_google_oauth_state(
                "state-123",
                "",
                "state-123",
                expires_at,
            )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GoogleDriveAccountStore.validate_google_oauth_state(
                "state-123",
                "different-state",
                "state-123",
                expires_at,
            )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GoogleDriveAccountStore.validate_google_oauth_state(
                "state-123",
                "state-123",
                "state-123",
                int(time.time()) - 1,
            )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GoogleDriveAccountStore.validate_google_oauth_state(
                "state-123",
                "state-123",
                "other-state",
                expires_at,
            )

    @patch("src.account_store.requests.request")
    def test_code_exchange_returns_verified_google_user_session(self, request):
        request.side_effect = [
            self.response(
                {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                }
            ),
            self.response(
                {
                    "sub": "google-user-id",
                    "email": "movie-fan@example.com",
                    "email_verified": True,
                    "name": "Movie Fan",
                }
            ),
        ]

        session = self.store.exchange_google_oauth_code(
            "one-time-code",
            "https://cinematch.example",
        )

        self.assertEqual(session["user_id"], "google-user-id")
        self.assertEqual(session["login"], "movie-fan@example.com")
        self.assertEqual(session["name"], "Movie Fan")
        self.assertEqual(session["access_token"], "access")
        self.assertEqual(session["refresh_token"], "refresh")
        token_call, profile_call = request.call_args_list
        self.assertEqual(token_call.args[:2], ("POST", self.store.TOKEN_URL))
        self.assertEqual(
            token_call.kwargs["data"],
            {
                "client_id": "client-id",
                "client_secret": "client-secret",
                "code": "one-time-code",
                "redirect_uri": "https://cinematch.example",
                "grant_type": "authorization_code",
            },
        )
        self.assertEqual(
            profile_call.args[:2],
            ("GET", self.store.USERINFO_URL),
        )
        self.assertEqual(
            profile_call.kwargs["headers"]["Authorization"],
            "Bearer access",
        )

    @patch("src.account_store.requests.request")
    def test_code_exchange_rejects_unverified_google_email(self, request):
        request.side_effect = [
            self.response({"access_token": "access"}),
            self.response(
                {
                    "sub": "google-user-id",
                    "email": "movie-fan@example.com",
                    "email_verified": False,
                }
            ),
        ]

        with self.assertRaisesRegex(AccountStoreError, "verified email"):
            self.store.exchange_google_oauth_code(
                "one-time-code",
                "https://cinematch.example",
            )

    @patch("src.account_store.requests.request")
    def test_expiring_google_session_can_be_refreshed(self, request):
        request.return_value = self.response(
            {"access_token": "new-access", "expires_in": 3600}
        )

        session = self.store.refresh_session(self.session)

        self.assertEqual(session["access_token"], "new-access")
        self.assertEqual(session["refresh_token"], "user-refresh-token")
        self.assertEqual(session["login"], "movie-fan@example.com")
        self.assertEqual(
            request.call_args.kwargs["data"],
            {
                "client_id": "client-id",
                "client_secret": "client-secret",
                "grant_type": "refresh_token",
                "refresh_token": "user-refresh-token",
            },
        )

    @patch("src.account_store.requests.request")
    def test_watchlist_reads_file_from_private_drive_app_data(self, request):
        request.side_effect = [
            self.response(
                {"files": [{"id": "file-1", "name": self.store.WATCHLIST_FILENAME}]}
            ),
            self.response(
                {"version": 1, "movies": [{"title": "A Movie"}]}
            ),
        ]

        movies = self.store.get_watchlist(self.session)

        self.assertEqual(movies, [{"title": "A Movie"}])
        self.assertEqual(self.session["drive_file_id"], "file-1")
        list_call, file_call = request.call_args_list
        self.assertEqual(
            list_call.args[:2],
            ("GET", f"{self.store.API_URL}/files"),
        )
        self.assertEqual(list_call.kwargs["params"]["spaces"], "appDataFolder")
        self.assertIn("appDataFolder", list_call.kwargs["params"]["q"])
        self.assertEqual(
            file_call.args[1],
            f"{self.store.API_URL}/files/file-1",
        )
        self.assertEqual(file_call.kwargs["params"], {"alt": "media"})

    @patch("src.account_store.requests.request")
    def test_save_creates_private_drive_file_and_uploads_watchlist(self, request):
        request.side_effect = [
            self.response({"files": []}),
            self.response({"id": "file-new"}),
            self.response(None, status_code=204),
        ]

        self.store.save_movie(
            self.session,
            {"title": "A Movie", "year": 2026, "tmdb_id": 42},
        )

        create_call, upload_call = request.call_args_list[1:]
        self.assertEqual(
            create_call.args[:2],
            ("POST", f"{self.store.API_URL}/files"),
        )
        self.assertEqual(
            create_call.kwargs["json"],
            {
                "name": self.store.WATCHLIST_FILENAME,
                "mimeType": "application/json",
                "parents": ["appDataFolder"],
            },
        )
        self.assertEqual(
            upload_call.args[:2],
            ("PATCH", f"{self.store.UPLOAD_URL}/files/file-new"),
        )
        self.assertEqual(upload_call.kwargs["params"], {"uploadType": "media"})
        self.assertEqual(
            json.loads(upload_call.kwargs["data"]),
            {
                "version": 1,
                "movies": [{"title": "A Movie", "year": 2026, "tmdb_id": 42}],
            },
        )
        self.assertEqual(self.session["drive_file_id"], "file-new")

    @patch("src.account_store.requests.request")
    def test_remove_and_clear_update_existing_drive_file(self, request):
        movie = {"title": "A Movie", "tmdb_id": 42}
        request.side_effect = [
            self.response({"version": 1, "movies": [movie]}),
            self.response(None, status_code=204),
            self.response({"version": 1, "movies": [movie]}),
            self.response(None, status_code=204),
        ]
        self.session["drive_file_id"] = "file-1"

        self.store.remove_movie(self.session, movie)
        self.store.clear_watchlist(self.session)

        upload_calls = [
            request_call
            for request_call in request.call_args_list
            if request_call.args[0] == "PATCH"
        ]
        self.assertEqual(len(upload_calls), 2)
        self.assertEqual(
            json.loads(upload_calls[0].kwargs["data"])["movies"],
            [],
        )
        self.assertEqual(
            json.loads(upload_calls[1].kwargs["data"])["movies"],
            [],
        )

    @patch("src.account_store.requests.request")
    def test_google_errors_are_reported(self, request):
        response = self.response(
            {"error": {"message": "Permission denied"}},
            status_code=403,
        )
        response.raise_for_status.side_effect = HTTPError("forbidden")
        request.return_value = response

        with self.assertRaisesRegex(AccountStoreError, "Permission denied"):
            self.store.get_watchlist(self.session)


if __name__ == "__main__":
    unittest.main()
