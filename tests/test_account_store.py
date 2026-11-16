import json
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from requests import HTTPError

from src.account_store import AccountStoreError, GitHubGistAccountStore


class GitHubGistAccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = GitHubGistAccountStore("client-id", "client-secret")
        self.session = {
            "access_token": "user-access-token",
            "expires_at": 1_900_000_000,
            "user_id": "42",
            "login": "movie-fan",
        }

    @staticmethod
    def response(payload, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.content = json.dumps(payload).encode()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    def test_oauth_request_uses_gist_scope_and_csrf_state(self):
        url = self.store.create_github_oauth_request(
            "https://cinematch.example",
            "one-time-state",
        )
        params = parse_qs(urlparse(url).query)

        self.assertEqual(urlparse(url).netloc, "github.com")
        self.assertEqual(params["client_id"], ["client-id"])
        self.assertEqual(params["redirect_uri"], ["https://cinematch.example"])
        self.assertEqual(params["scope"], ["gist"])
        self.assertEqual(params["state"], ["one-time-state"])

    def test_oauth_request_rejects_non_https_redirect(self):
        with self.assertRaisesRegex(AccountStoreError, "HTTPS"):
            self.store.create_github_oauth_request(
                "http://cinematch.example",
                "one-time-state",
            )

    def test_oauth_state_requires_matching_browser_and_unexpired_state(self):
        expires_at = int(time.time()) + 600

        GitHubGistAccountStore.validate_github_oauth_state(
            "state-123",
            "state-123",
            "state-123",
            expires_at,
        )
        GitHubGistAccountStore.validate_github_oauth_state(
            "state-123",
            "",
            "state-123",
            0,
        )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GitHubGistAccountStore.validate_github_oauth_state(
                "state-123",
                "different-state",
                "state-123",
                expires_at,
            )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GitHubGistAccountStore.validate_github_oauth_state(
                "state-123",
                "state-123",
                "state-123",
                int(time.time()) - 1,
            )
        with self.assertRaisesRegex(AccountStoreError, "state is invalid or expired"):
            GitHubGistAccountStore.validate_github_oauth_state(
                "state-123",
                "",
                "other-state",
                0,
            )

    @patch("src.account_store.requests.request")
    def test_code_exchange_returns_github_user_session(self, request):
        request.side_effect = [
            self.response(
                {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                    "scope": "gist",
                }
            ),
            self.response({"id": 42, "login": "movie-fan"}),
        ]

        session = self.store.exchange_github_oauth_code(
            "one-time-code",
            "one-time-state",
            "https://cinematch.example",
        )

        self.assertEqual(session["user_id"], "42")
        self.assertEqual(session["login"], "movie-fan")
        self.assertEqual(session["access_token"], "access")
        self.assertEqual(session["refresh_token"], "refresh")
        exchange_call, profile_call = request.call_args_list
        self.assertEqual(
            exchange_call.args[:2],
            (
                "POST",
                "https://github.com/login/oauth/access_token",
            ),
        )
        self.assertEqual(
            exchange_call.kwargs["data"],
            {
                "client_id": "client-id",
                "client_secret": "client-secret",
                "code": "one-time-code",
                "redirect_uri": "https://cinematch.example",
                "state": "one-time-state",
            },
        )
        self.assertEqual(
            exchange_call.kwargs["headers"]["Content-Type"],
            "application/x-www-form-urlencoded",
        )
        self.assertEqual(
            exchange_call.kwargs["headers"]["Accept"],
            "application/json",
        )
        self.assertEqual(profile_call.args[:2], ("GET", "https://api.github.com/user"))
        self.assertEqual(
            profile_call.kwargs["headers"]["Authorization"],
            "Bearer access",
        )

    @patch("src.account_store.requests.request")
    def test_code_exchange_rejects_token_without_gist_scope(self, request):
        request.return_value = self.response({"access_token": "access", "scope": ""})

        with self.assertRaisesRegex(AccountStoreError, "Gist permission"):
            self.store.exchange_github_oauth_code(
                "one-time-code",
                "one-time-state",
                "https://cinematch.example",
            )

        request.assert_called_once()

    @patch("src.account_store.requests.request")
    def test_expiring_github_session_can_be_refreshed(self, request):
        request.return_value = self.response(
            {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
            }
        )

        session = self.store.refresh_session(
            {
                **self.session,
                "access_token": "old-access",
                "refresh_token": "old-refresh",
            }
        )

        self.assertEqual(session["access_token"], "new-access")
        self.assertEqual(session["refresh_token"], "new-refresh")
        self.assertEqual(session["login"], "movie-fan")
        self.assertEqual(
            request.call_args.kwargs["data"],
            {
                "client_id": "client-id",
                "client_secret": "client-secret",
                "grant_type": "refresh_token",
                "refresh_token": "old-refresh",
            },
        )

    @patch("src.account_store.requests.request")
    def test_watchlist_reads_matching_gist_with_user_token(self, request):
        request.side_effect = [
            self.response(
                [
                    {
                        "id": "gist-1",
                        "description": self.store.GIST_DESCRIPTION,
                        "files": {self.store.WATCHLIST_FILENAME: {}},
                    }
                ]
            ),
            self.response(
                {
                    "id": "gist-1",
                    "files": {
                        self.store.WATCHLIST_FILENAME: {
                            "content": json.dumps(
                                {"version": 1, "movies": [{"title": "A Movie"}]}
                            )
                        }
                    },
                }
            ),
        ]

        result = self.store.get_watchlist(self.session)

        self.assertEqual(result, [{"title": "A Movie"}])
        self.assertEqual(self.session["gist_id"], "gist-1")
        list_call, gist_call = request.call_args_list
        self.assertEqual(list_call.args[:2], ("GET", "https://api.github.com/gists"))
        self.assertEqual(
            list_call.kwargs["headers"]["Authorization"],
            "Bearer user-access-token",
        )
        self.assertEqual(gist_call.args[1], "https://api.github.com/gists/gist-1")

    @patch("src.account_store.requests.request")
    def test_save_creates_unlisted_gist_with_watchlist_data(self, request):
        request.side_effect = [
            self.response([]),
            self.response({"id": "gist-new"}, status_code=201),
        ]

        self.store.save_movie(
            self.session,
            {"title": "A Movie", "year": 2026, "tmdb_id": 42},
        )

        create_call = request.call_args_list[1]
        self.assertEqual(create_call.args[:2], ("POST", "https://api.github.com/gists"))
        self.assertEqual(
            create_call.kwargs["headers"]["Authorization"],
            "Bearer user-access-token",
        )
        body = create_call.kwargs["json"]
        self.assertFalse(body["public"])
        self.assertEqual(body["description"], self.store.GIST_DESCRIPTION)
        self.assertEqual(
            json.loads(body["files"][self.store.WATCHLIST_FILENAME]["content"]),
            {
                "version": 1,
                "movies": [{"title": "A Movie", "year": 2026, "tmdb_id": 42}],
            },
        )
        self.assertEqual(self.session["gist_id"], "gist-new")

    @patch("src.account_store.requests.request")
    def test_remove_and_clear_update_existing_gist(self, request):
        movie = {"title": "A Movie", "tmdb_id": 42}
        request.side_effect = [
            self.response(
                {
                    "files": {
                        self.store.WATCHLIST_FILENAME: {
                            "content": json.dumps({"version": 1, "movies": [movie]})
                        }
                    }
                }
            ),
            self.response({}, status_code=200),
            self.response(
                {
                    "files": {
                        self.store.WATCHLIST_FILENAME: {
                            "content": json.dumps({"version": 1, "movies": [movie]})
                        }
                    }
                }
            ),
            self.response({}, status_code=200),
        ]
        self.session["gist_id"] = "gist-1"

        self.store.remove_movie(self.session, movie)
        self.store.clear_watchlist(self.session)

        patch_calls = [call for call in request.call_args_list if call.args[0] == "PATCH"]
        self.assertEqual(len(patch_calls), 2)
        self.assertEqual(
            json.loads(
                patch_calls[0].kwargs["json"]["files"][
                    self.store.WATCHLIST_FILENAME
                ]["content"]
            )["movies"],
            [],
        )
        self.assertEqual(
            json.loads(
                patch_calls[1].kwargs["json"]["files"][
                    self.store.WATCHLIST_FILENAME
                ]["content"]
            )["movies"],
            [],
        )

    @patch("src.account_store.requests.request")
    def test_github_errors_are_reported(self, request):
        response = self.response({"message": "Bad credentials"}, status_code=401)
        response.raise_for_status.side_effect = HTTPError("unauthorized")
        request.return_value = response

        with self.assertRaisesRegex(AccountStoreError, "Bad credentials"):
            self.store.get_watchlist(self.session)


if __name__ == "__main__":
    unittest.main()
