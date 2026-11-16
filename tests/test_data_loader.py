import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import src.data_loader as data_loader


class AddMoviesToDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "movies.csv"
        pd.DataFrame(
            [
                {
                    "id": 1,
                    "title": "Existing Movie",
                    "year": 2000,
                    "genres": "Drama",
                    "director": "A Director",
                    "cast": "An Actor",
                    "rating": 7.0,
                    "votes": 10,
                    "runtime": 100,
                    "moods": "Thoughtful",
                    "tagline": "A tagline",
                    "overview": "An existing film.",
                    "keywords": "film",
                    "poster_url": "poster",
                    "backdrop_url": "backdrop",
                    "trailer_url": "trailer",
                    "box_office": "N/A",
                }
            ]
        ).to_csv(self.csv_path, index=False)
        self.path_patch = patch.object(data_loader, "DATA_PATH", self.csv_path)
        self.path_patch.start()
        data_loader.load_movie_data.clear()

    def tearDown(self):
        data_loader.load_movie_data.clear()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_batch_add_skips_existing_and_batch_duplicates(self):
        movies = [
            {"title": "Existing Movie", "year": 2000, "rating": 7.0, "runtime": 100},
            {"title": "New Movie", "year": 2020, "rating": 8.0, "runtime": 110},
            {"title": "New Movie", "year": 2020, "rating": 8.0, "runtime": 110},
        ]

        added = data_loader.add_movies_to_dataset(movies)
        result = pd.read_csv(self.csv_path)

        self.assertEqual(added, 1)
        self.assertEqual(result["title"].tolist(), ["Existing Movie", "New Movie"])
        self.assertEqual(result["id"].tolist(), [1, 2])

    def test_prompt_recommender_ranks_related_movie_metadata(self):
        movies = pd.DataFrame(
            [
                {
                    "title": "Space Journey",
                    "year": 2020,
                    "genres": "Sci-Fi, Drama",
                    "director": "A Director",
                    "cast": "An Actor",
                    "moods": "Emotional",
                    "tagline": "",
                    "overview": "A family explores a distant planet together.",
                    "keywords": "space travel, family, exploration",
                    "certification": "PG-13",
                    "rating": 8.0,
                    "votes": 1000,
                    "runtime": 120,
                },
                {
                    "title": "City Comedy",
                    "year": 2021,
                    "genres": "Comedy",
                    "director": "Another Director",
                    "cast": "Another Actor",
                    "moods": "Funny",
                    "tagline": "",
                    "overview": "Friends find themselves in a silly city adventure.",
                    "keywords": "friendship, comedy",
                    "certification": "PG",
                    "rating": 6.5,
                    "votes": 2000,
                    "runtime": 100,
                },
            ]
        )
        recommender = data_loader.MovieRecommender(movies)

        results = recommender.recommend_for_prompt(
            "emotional family exploring space",
            top_n=2,
            genre_filter=["Sci-Fi"],
            min_rating=7.5,
            year_range=(2019, 2022),
        )

        self.assertEqual([movie["title"] for movie in results], ["Space Journey"])
        self.assertIn("match_reasons", results[0])

        strict_results = recommender.recommend_for_prompt(
            "emotional family exploring space",
            min_relevance=100,
        )
        self.assertEqual(strict_results, [])

    def test_prompt_genres_filter_out_unrelated_movies(self):
        movies = pd.DataFrame(
            [
                {
                    "title": "Family Comedy",
                    "year": 2020,
                    "genres": "Animation, Comedy, Family",
                    "director": "A Director",
                    "cast": "An Actor",
                    "moods": "Heartwarming",
                    "tagline": "",
                    "overview": "A funny adventure for the whole family.",
                    "keywords": "children, friendship",
                    "certification": "PG",
                    "rating": 8.0,
                    "votes": 1000,
                    "runtime": 100,
                },
                {
                    "title": "Family Horror",
                    "year": 2020,
                    "genres": "Drama, Horror, Family",
                    "director": "Another Director",
                    "cast": "Another Actor",
                    "moods": "Disturbing",
                    "tagline": "",
                    "overview": "A family faces a disturbing haunting.",
                    "keywords": "family trauma, frightening",
                    "certification": "R",
                    "rating": 8.0,
                    "votes": 1000,
                    "runtime": 100,
                },
            ]
        )
        recommender = data_loader.MovieRecommender(movies)

        results = recommender.recommend_for_prompt("family friendly comedy")

        self.assertEqual([movie["title"] for movie in results], ["Family Comedy"])

    def test_prompt_recommender_applies_runtime_and_vote_filters(self):
        movies = pd.DataFrame(
            [
                {
                    "title": "Short Space Story",
                    "year": 2020,
                    "genres": "Sci-Fi",
                    "director": "A Director",
                    "cast": "An Actor",
                    "moods": "Wonder",
                    "tagline": "",
                    "overview": "A family explores a distant planet.",
                    "keywords": "space exploration, family",
                    "certification": "PG",
                    "rating": 8.0,
                    "votes": 900,
                    "runtime": 95,
                },
                {
                    "title": "Long Space Story",
                    "year": 2021,
                    "genres": "Sci-Fi",
                    "director": "Another Director",
                    "cast": "Another Actor",
                    "moods": "Wonder",
                    "tagline": "",
                    "overview": "A family explores a distant planet.",
                    "keywords": "space exploration, family",
                    "certification": "PG",
                    "rating": 8.0,
                    "votes": 900,
                    "runtime": 125,
                },
                {
                    "title": "Popular Space Story",
                    "year": 2022,
                    "genres": "Sci-Fi",
                    "director": "Third Director",
                    "cast": "Third Actor",
                    "moods": "Wonder",
                    "tagline": "",
                    "overview": "A family explores a distant planet.",
                    "keywords": "space exploration, family",
                    "certification": "PG",
                    "rating": 8.0,
                    "votes": 400,
                    "runtime": 125,
                },
            ]
        )
        recommender = data_loader.MovieRecommender(movies)

        results = recommender.recommend_for_prompt(
            "space exploration",
            min_runtime=100,
            max_runtime=140,
            min_votes=500,
        )

        self.assertEqual([movie["title"] for movie in results], ["Long Space Story"])

    def test_prompt_recommender_uses_similar_titles_when_title_is_prompted(self):
        frame = pd.DataFrame(
            [
                {
                    "title": "Inception",
                    "year": 2010,
                    "genres": "Sci-Fi, Action",
                    "director": "A Director",
                    "cast": "An Actor",
                    "moods": "Mind-Bending",
                    "tagline": "",
                    "overview": "A mind-bending journey through dreams and space.",
                    "keywords": "dreams, space travel, reality",
                    "certification": "PG-13",
                    "rating": 8.8,
                    "votes": 2000,
                    "runtime": 140,
                },
                {
                    "title": "Dreams Beyond",
                    "year": 2022,
                    "genres": "Sci-Fi, Action",
                    "director": "Another Director",
                    "cast": "Another Actor",
                    "moods": "Mind-Bending",
                    "tagline": "",
                    "overview": "A mind-bending story about dreams and space travel.",
                    "keywords": "dreams, space travel, reality",
                    "certification": "PG-13",
                    "rating": 8.0,
                    "votes": 500,
                    "runtime": 120,
                },
            ]
        )
        recommender = data_loader.MovieRecommender(frame)

        results = recommender.recommend_for_prompt("movies like Inception", top_n=3)

        self.assertTrue(results)
        self.assertNotEqual(results[0]["title"], "Inception")


if __name__ == "__main__":
    unittest.main()
