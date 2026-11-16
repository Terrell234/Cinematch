import base64
import hashlib
import json
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from requests import HTTPError

from src.account_store import AccountStoreError, SupabaseAccountStore


class SupabaseAccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseAccountStore("https://example.supabase.co/", "anon-key")
        self.session = {
            "access_token": "user-access-token",
            "refresh_token": "refresh-token",
            "expires_at": 1_900_000_000,
            "user_id": "user-123",
            "email": "movie.fan@example.com",
        }

    @staticmethod
    def response(payload, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.content = b"response"
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    @patch("src.account_store.requests.request")
    def test_sign_in_returns_user_session(self, request):
        request.return_value = self.response(
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
                "user": {"id": "user-123", "email": "movie.fan@example.com"},
            }
        )

        result = self.store.sign_in("movie.fan@example.com", "password")

        self.assertEqual(result["user_id"], "user-123")
        self.assertEqual(result["email"], "movie.fan@example.com")
        self.assertEqual(result["access_token"], "access")
        call = request.call_args
        self.assertEqual(call.args[:2], ("POST", "https://example.supabase.co/auth/v1/token?grant_type=password"))
        self.assertEqual(call.kwargs["headers"]["apikey"], "anon-key")
        self.assertEqual(call.kwargs["json"], {"email": "movie.fan@example.com", "password": "password"})

    def test_signup_without_email_confirmation_session_returns_none(self):
        with patch.object(self.store, "_request", return_value={"user": {"id": "user-123"}}):
            self.assertIsNone(self.store.sign_up("movie.fan@example.com", "password"))

    def test_account_service_requires_https(self):
        with self.assertRaisesRegex(AccountStoreError, "HTTPS"):
            SupabaseAccountStore("http://example.supabase.co", "anon-key")

    def test_account_service_rejects_service_role_key(self):
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "service_role"}).encode()
        ).decode().rstrip("=")
        service_role_key = f"header.{payload}.signature"

        with self.assertRaisesRegex(AccountStoreError, "never the service_role key"):
            SupabaseAccountStore("https://example.supabase.co", service_role_key)

    def test_github_oauth_request_uses_pkce_and_encrypted_callback_state(self):
        authorization_url, nonce = self.store.create_github_oauth_request(
            "https://cinematch.example",
            "test state encryption secret",
        )
        auth_params = parse_qs(urlparse(authorization_url).query)
        callback_params = parse_qs(urlparse(auth_params["redirect_to"][0]).query)
        encrypted_state = callback_params["oauth_state"][0]

        self.assertEqual(auth_params["provider"], ["github"])
        self.assertEqual(auth_params["code_challenge_method"], ["s256"])
        self.assertTrue(auth_params["code_challenge"][0])
        self.assertTrue(encrypted_state)
        self.assertTrue(nonce)

        with patch.object(
            self.store,
            "_request",
            return_value={
                "access_token": "access",
                "refresh_token": "refresh",
                "user": {"id": "user-123"},
            },
        ) as exchange:
            session = self.store.exchange_github_oauth_code(
                "one-time-code",
                encrypted_state,
                nonce,
                "test state encryption secret",
            )

        verifier = exchange.call_args.kwargs["body"]["code_verifier"]
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        self.assertEqual(auth_params["code_challenge"], [expected_challenge])
        self.assertEqual(exchange.call_args.args[:2], ("POST", "auth/v1/token?grant_type=pkce"))
        self.assertEqual(
            exchange.call_args.kwargs["body"],
            {"auth_code": "one-time-code", "code_verifier": verifier},
        )
        self.assertEqual(session["user_id"], "user-123")

    def test_github_oauth_rejects_state_from_another_browser(self):
        _, nonce = self.store.create_github_oauth_request(
            "https://cinematch.example",
            "test state encryption secret",
        )
        authorization_url, _ = self.store.create_github_oauth_request(
            "https://cinematch.example",
            "test state encryption secret",
        )
        state = parse_qs(urlparse(authorization_url).query)["redirect_to"][0]
        encrypted_state = parse_qs(urlparse(state).query)["oauth_state"][0]

        with patch.object(self.store, "_request") as exchange:
            with self.assertRaisesRegex(AccountStoreError, "invalid or expired"):
                self.store.exchange_github_oauth_code(
                    "one-time-code",
                    encrypted_state,
                    nonce,
                    "test state encryption secret",
                )
        exchange.assert_not_called()

    @patch("src.account_store.requests.request")
    def test_watchlist_reads_only_current_user_rows_with_user_token(self, request):
        request.return_value = self.response(
            [{"movie_id": "tmdb:42", "movie_data": {"title": "A Movie"}}]
        )

        result = self.store.get_watchlist(self.session)

        self.assertEqual(result, [{"title": "A Movie"}])
        call = request.call_args
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer user-access-token")
        self.assertEqual(
            call.kwargs["params"]["user_id"],
            "eq.user-123",
        )

    @patch("src.account_store.requests.request")
    def test_save_uses_user_jwt_and_scoped_upsert(self, request):
        request.return_value = self.response({}, status_code=201)

        self.store.save_movie(self.session, {"title": "A Movie", "year": 2026, "tmdb_id": 42})

        call = request.call_args
        self.assertEqual(
            call.args[1],
            "https://example.supabase.co/rest/v1/user_watchlists?on_conflict=user_id,movie_id",
        )
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer user-access-token")
        self.assertEqual(
            call.kwargs["json"],
            {
                "user_id": "user-123",
                "movie_id": "tmdb:42",
                "movie_data": {"title": "A Movie", "year": 2026, "tmdb_id": 42},
            },
        )

    @patch("src.account_store.requests.request")
    def test_remove_movie_is_scoped_to_the_current_user(self, request):
        request.return_value = self.response({}, status_code=204)

        self.store.remove_movie(self.session, {"title": "A Movie", "year": 2026, "tmdb_id": 42})

        call = request.call_args
        self.assertEqual(call.args[0], "DELETE")
        self.assertEqual(
            call.kwargs["params"],
            {"user_id": "eq.user-123", "movie_id": "eq.tmdb:42"},
        )
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer user-access-token")

    @patch("src.account_store.requests.request")
    def test_service_errors_are_reported_without_silent_fallback(self, request):
        response = self.response({"msg": "Invalid login credentials"}, status_code=400)
        response.raise_for_status.side_effect = HTTPError("bad request")
        request.return_value = response

        with self.assertRaisesRegex(AccountStoreError, "Invalid login credentials"):
            self.store.sign_in("movie.fan@example.com", "bad-password")


if __name__ == "__main__":
    unittest.main()
