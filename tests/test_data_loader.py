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


if __name__ == "__main__":
    unittest.main()
