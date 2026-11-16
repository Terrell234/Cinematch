# CineMatch AI

CineMatch is a Streamlit movie-discovery app with a dark cinema theme, content-based recommendations, mood matching, movie blends, watchlists, analytics, and optional live movie data from TMDB. Its TMDB discovery page can recommend movies based on a selected title and filter live results by rating, release year, and genre.

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

   The TMDB integration is optional; the curated catalog and recommendation features work without a key. You can also enter a key in the app sidebar for the current session.

For local development, copy `.env.example` to `.env` and set `TMDB_API_KEY` there. Keep API credentials out of GitHub: `.env` and Streamlit's `secrets.toml` are excluded by `.gitignore`.

## Catalog tools

- `python build_dataset.py` regenerates the curated starter catalog.
- `python add_category_movies.py` appends the additional category titles. If `TMDB_API_KEY` is set in the environment or `.env`, it also looks up images and trailers.
- `python enrich_with_tmdb.py` and `python fetch_backdrops.py` optionally enrich catalog artwork using TMDB.

Movies imported through the live TMDB browser are written to the app's local catalog. Streamlit Community Cloud's filesystem is ephemeral, so those imports are not a permanent replacement for updating and pushing the CSV in the GitHub repository.
