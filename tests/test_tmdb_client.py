import unittest
from unittest.mock import Mock

from src.tmdb_client import TMDBClient


class TMDBClientTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
