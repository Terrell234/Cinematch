import unittest
from unittest.mock import Mock, call, patch

from src.tmdb_client import TMDBClient


class TMDBClientTests(unittest.TestCase):
    def test_client_reads_tmdb_api_key_from_environment(self):
        with patch.dict("os.environ", {"TMDB_API_KEY": "env-test-key"}):
            client = TMDBClient()

        self.assertTrue(client.is_configured)
        self.assertEqual(client.params, {"api_key": "env-test-key"})

    def test_client_reads_tmdb_api_token_from_environment(self):
        token = "eyJtest-access-token"
        with patch.dict("os.environ", {"TMDB_API_KEY": "", "TMDB_API_TOKEN": token}):
            client = TMDBClient()

        self.assertTrue(client.is_configured)
        self.assertEqual(client.session.headers["Authorization"], f"Bearer {token}")

    def test_search_movies_can_scope_results_to_year(self):
        client = TMDBClient("test-key")
        response = Mock()
        response.json.return_value = {"results": [{"id": 1, "title": "A Movie"}]}
        response.raise_for_status.return_value = None
        client.session.get = Mock(return_value=response)

        results = client.search_movies("A Movie", year=2024)

        self.assertEqual(results, [{"id": 1, "title": "A Movie"}])
        client.session.get.assert_called_once_with(
            "https://api.themoviedb.org/3/search/movie",
            params={
                "api_key": "test-key",
                "query": "A Movie",
                "include_adult": "false",
                "year": 2024,
            },
            timeout=12,
        )

    def test_catalog_poster_retries_unscoped_search_for_exact_title_and_year(self):
        client = TMDBClient("test-key")
        with patch.object(
            client,
            "search_movies",
            side_effect=[
                [
                    {
                        "id": 1,
                        "title": "A Movie",
                        "release_date": "2023-01-01",
                        "poster_path": "/wrong-year.jpg",
                    }
                ],
                [
                    {
                        "id": 2,
                        "title": "A Movie",
                        "release_date": "2024-01-01",
                        "poster_path": "/matching.jpg",
                    }
                ],
            ],
        ) as search_movies:
            poster = client.get_catalog_poster("A Movie", 2024)

        self.assertEqual(
            poster["poster_url"],
            "https://image.tmdb.org/t/p/w500/matching.jpg",
        )
        self.assertEqual(
            search_movies.call_args_list,
            [call("A Movie", year=2024), call("A Movie")],
        )

    def test_movie_recommendations_use_tmdb_endpoint(self):
        client = TMDBClient("test-key")
        response = Mock()
        response.json.return_value = {"results": [{"id": 42, "title": "A Movie"}]}
        response.raise_for_status.return_value = None

        client.session.get = Mock(return_value=response)

        results = client.get_movie_recommendations(123, page=2)

        self.assertEqual(results, [{"id": 42, "title": "A Movie"}])
        client.session.get.assert_called_once_with(
            "https://api.themoviedb.org/3/movie/123/recommendations",
            params={"api_key": "test-key", "page": 2},
            timeout=12,
        )

    def test_movie_details_request_credits_keywords_and_release_ratings(self):
        client = TMDBClient("test-key")
        response = Mock()
        response.json.return_value = {"id": 42, "title": "A Movie"}
        response.raise_for_status.return_value = None
        client.session.get = Mock(return_value=response)

        result = client.get_movie_details(42)

        self.assertEqual(result["title"], "A Movie")
        client.session.get.assert_called_once_with(
            "https://api.themoviedb.org/3/movie/42",
            params={
                "api_key": "test-key",
                "append_to_response": "credits,videos,keywords,release_dates",
            },
            timeout=12,
        )

    def test_popular_movies_use_discover_endpoint(self):
        client = TMDBClient("test-key")
        response = Mock()
        response.json.return_value = {"results": [{"id": 42, "title": "A Movie"}]}
        response.raise_for_status.return_value = None

        client.session.get = Mock(return_value=response)

        results = client.get_popular_movies(page=3)

        self.assertEqual(results, [{"id": 42, "title": "A Movie"}])
        client.session.get.assert_called_once_with(
            "https://api.themoviedb.org/3/discover/movie",
            params={
                "api_key": "test-key",
                "page": 3,
                "sort_by": "popularity.desc",
                "include_adult": "false",
                "include_video": "false",
                "vote_count.gte": 50,
            },
            timeout=12,
        )

    def test_filter_movie_results_applies_genre_rating_and_year(self):
        movies = [
            {"id": 1, "vote_average": 8.0, "release_date": "2024-01-01", "genre_ids": [878]},
            {"id": 2, "vote_average": 9.0, "release_date": "2021-01-01", "genre_ids": [878]},
            {"id": 3, "vote_average": 9.0, "release_date": "2024-01-01", "genre_ids": [28]},
        ]

        results = TMDBClient.filter_movie_results(
            movies,
            genre_ids={878},
            min_rating=7.5,
            year_range=(2022, 2025),
        )

        self.assertEqual([movie["id"] for movie in results], [1])

    def test_filter_movie_results_applies_runtime_and_vote_constraints(self):
        movies = [
            {
                "id": 1,
                "vote_average": 8.0,
                "vote_count": 900,
                "release_date": "2024-01-01",
                "runtime": 120,
            },
            {
                "id": 2,
                "vote_average": 8.0,
                "vote_count": 400,
                "release_date": "2024-01-01",
                "runtime": 120,
            },
            {
                "id": 3,
                "vote_average": 8.0,
                "vote_count": 900,
                "release_date": "2024-01-01",
                "runtime": 90,
            },
        ]

        results = TMDBClient.filter_movie_results(
            movies,
            runtime_range=(100, 140),
            min_votes=500,
        )

        self.assertEqual([movie["id"] for movie in results], [1])

    def test_format_tmdb_movie_maps_discover_genres(self):
        client = TMDBClient()

        movie = client.format_tmdb_movie(
            {
                "title": "A Movie",
                "release_date": "2024-05-01",
                "genre_ids": [878, 12],
                "vote_average": 8.2,
            }
        )

        self.assertEqual(movie["genres"], "Sci-Fi, Adventure")
        self.assertEqual(movie["year"], 2024)
        self.assertEqual(movie["runtime"], 0)

    def test_catalog_search_posters_require_matching_title_and_year(self):
        client = TMDBClient()

        matched, unmatched = client.match_catalog_search_posters(
            [{"title": "A Movie", "year": 2024}],
            [
                {
                    "id": 1,
                    "title": "A Movie",
                    "release_date": "2024-05-01",
                    "poster_path": "/matching.jpg",
                },
                {
                    "id": 2,
                    "title": "A Movie",
                    "release_date": "2020-05-01",
                    "poster_path": "/different-year.jpg",
                },
            ],
        )

        self.assertEqual(
            matched[("a movie", 2024)]["poster_url"],
            "https://image.tmdb.org/t/p/w500/matching.jpg",
        )
        self.assertEqual(matched[("a movie", 2024)]["tmdb_id"], 1)
        self.assertEqual([movie["id"] for movie in unmatched], [2])

    def test_format_tmdb_movie_includes_search_detail_fields(self):
        client = TMDBClient()

        movie = client.format_tmdb_movie(
            {
                "title": "A Movie",
                "release_date": "2024-05-01",
                "runtime": 128,
                "genres": [{"name": "Drama"}],
                "credits": {
                    "cast": [{"name": "Lead Actor"}, {"name": "Supporting Actor"}],
                    "crew": [{"name": "Film Director", "job": "Director"}],
                },
                "videos": {
                    "results": [
                        {
                            "site": "YouTube",
                            "type": "Trailer",
                            "key": "trailer-key",
                        }
                    ]
                },
                "keywords": {"keywords": [{"name": "family"}, {"name": "space travel"}]},
                "release_dates": {
                    "results": [
                        {
                            "iso_3166_1": "US",
                            "release_dates": [{"certification": "PG-13"}],
                        }
                    ]
                },
                "budget": 100000000,
                "revenue": 250000000,
                "status": "Released",
                "original_language": "en",
            }
        )

        self.assertEqual(movie["runtime"], 128)
        self.assertEqual(movie["genres"], "Drama")
        self.assertEqual(movie["cast"], "Lead Actor, Supporting Actor")
        self.assertEqual(movie["director"], "Film Director")
        self.assertEqual(movie["certification"], "PG-13")
        self.assertEqual(movie["keywords"], "family, space travel")
        self.assertEqual(movie["budget"], 100000000)
        self.assertEqual(movie["revenue"], 250000000)
        self.assertEqual(movie["box_office"], "$250,000,000")
        self.assertEqual(movie["status"], "Released")
        self.assertEqual(movie["original_language"], "en")
        self.assertEqual(movie["trailer_url"], "https://www.youtube.com/watch?v=trailer-key")

    def test_trailer_url_prefers_official_youtube_trailer(self):
        trailer_url = TMDBClient.get_trailer_url(
            {
                "videos": {
                    "results": [
                        {
                            "site": "YouTube",
                            "type": "Trailer",
                            "key": "unofficial-key",
                            "official": False,
                        },
                        {
                            "site": "YouTube",
                            "type": "Trailer",
                            "key": "official-key",
                            "official": True,
                        },
                        {
                            "site": "YouTube",
                            "type": "Teaser",
                            "key": "teaser-key",
                            "official": True,
                        },
                    ]
                }
            }
        )

        self.assertEqual(
            trailer_url,
            "https://www.youtube.com/watch?v=official-key",
        )

    def test_trailer_url_is_empty_when_tmdb_has_no_youtube_trailer(self):
        self.assertEqual(
            TMDBClient.get_trailer_url(
                {"videos": {"results": [{"site": "Vimeo", "type": "Trailer", "key": "x"}]}}
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
