import unittest

from src.watchlist import add_movie, movie_id, remove_movie


class WatchlistTests(unittest.TestCase):
    def test_add_movie_deduplicates_by_tmdb_id_and_updates_movie(self):
        original = {"title": "Original title", "tmdb_id": 42}
        updated = {"title": "Updated title", "tmdb_id": 42}

        watchlist = add_movie([original], updated)

        self.assertEqual(watchlist, [updated])

    def test_catalog_movies_use_normalized_title_and_year_identity(self):
        self.assertEqual(
            movie_id({"title": "A Movie", "year": 2024}),
            movie_id({"title": " a movie ", "year": "2024"}),
        )

    def test_remove_movie_matches_tmdb_identity(self):
        saved = [
            {"title": "A Movie", "tmdb_id": 42},
            {"title": "Another Movie", "tmdb_id": 99},
        ]

        self.assertEqual(
            remove_movie(saved, {"title": "A Movie", "tmdb_id": 42}),
            [saved[1]],
        )


if __name__ == "__main__":
    unittest.main()
