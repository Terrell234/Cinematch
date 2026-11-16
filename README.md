# CineMatch AI

CineMatch is a Streamlit movie-discovery app with a dark cinema theme, content-based recommendations, mood matching, movie blends, watchlists, analytics, and optional live movie data from TMDB. The top search accepts a movie title or a free-text description (for example, “emotional space adventure about family”) and ranks catalog recommendations by their plot, keywords, genre, cast, director, and other metadata. Filters include adjustable rating, release-year and runtime ranges, genres, and minimum vote count; they carry through catalog recommendations and movie collections. Collections can also be sorted by rating, votes, release date, or runtime.

Recommendation cards show the catalog's available information. With `TMDB_API_KEY` configured, the app enriches title/year-matched movies with TMDB certification, plot, keywords, cast, director, runtime, rating, vote count, budget, box office, and other movie details. Information TMDB does not provide is left unavailable rather than guessed.

Movie artwork is displayed only from TMDB's image host. Posters on catalog movie cards throughout the app are accepted only when a TMDB result exactly matches both the movie title and release year; otherwise the app shows a neutral placeholder instead of unrelated artwork. Live TMDB feeds use the poster attached to the same TMDB movie record.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_dataset.py
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). The bundled CSV contains the curated starter catalog. To add the extra category titles, run `python add_category_movies.py`.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app**, choose this repository and branch, and set **Main file path** to `app.py` (the file at the repository root).
3. Deploy. Streamlit installs the dependencies from `requirements.txt`; the movie catalog is committed at `data/movies.csv`.
4. Optional: in the app's **Settings → Secrets**, add:

   ```toml
   TMDB_API_KEY = "your-tmdb-api-key"
   ```

   The TMDB integration is optional; the curated catalog and recommendation features work without a key. You can also enter a key in the app's **Configure TMDB API key** panel for the current session.
   After deployment, open **Filters and TMDB settings** and select **Test TMDB** to verify the secret is accepted and live movie data can be loaded.

For local development, copy `.env.example` to `.env` and set `TMDB_API_KEY` there. Keep API credentials out of GitHub: `.env` and Streamlit's `secrets.toml` are excluded by `.gitignore`.

## Catalog tools

- `python build_dataset.py` regenerates the curated starter catalog.
- `python add_category_movies.py` appends the additional category titles. If `TMDB_API_KEY` is set in the environment or `.env`, it also looks up images and trailers.
- `python enrich_with_tmdb.py` and `python fetch_backdrops.py` optionally enrich catalog artwork using TMDB.

Movies imported through the live TMDB browser are written to the app's local catalog. Streamlit Community Cloud's filesystem is ephemeral, so those imports are not a permanent replacement for updating and pushing the CSV in the GitHub repository.

With `TMDB_API_KEY` configured, use **TMDB Live Discovery → Expand the recommendation catalog with TMDB** to import up to 100 popular titles at a time. Existing titles are skipped. Cloud imports are temporary; add desired titles to `data/movies.csv` and push the updated file to keep them across redeployments.
