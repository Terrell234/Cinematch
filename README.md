# CineMatch AI

CineMatch is a Streamlit movie-discovery app with a dark cinema theme, content-based recommendations, mood matching, movie blends, watchlists, analytics, and optional live movie data from TMDB. The top search accepts a movie title or a free-text description (for example, “emotional space adventure about family”) and ranks catalog recommendations by their plot, keywords, genre, cast, director, and other metadata. Button-based filters let users choose a minimum rating, release decade, runtime band, minimum vote count, and any combination of genres; these carry through catalog recommendations and movie collections. Collections can also be sorted by rating, votes, release date, or runtime.

Recommendation cards show the catalog's available information. With `TMDB_API_KEY` configured, the app enriches title/year-matched movies with TMDB certification, plot, keywords, cast, director, runtime, rating, vote count, budget, box office, and other movie details. Information TMDB does not provide is left unavailable rather than guessed.

Movie artwork is displayed only from TMDB's image host. Posters on catalog movie cards throughout the app are accepted only when a TMDB result exactly matches both the movie title and release year; otherwise the app shows a neutral placeholder instead of unrelated artwork. Live TMDB feeds use the poster attached to the same TMDB movie record.

Movie collections, recommendation cards, roulette picks, and saved-movie cards omit titles without a verified poster. Connect a TMDB key or read token to display the curated catalog. The Browse tab includes an Upcoming Movies category powered by TMDB, with the same genre, rating, year, runtime, vote, poster, trailer, sorting, and import features as the other live categories.

When direct similar-movie or prompt matches are unavailable, CineMatch offers clearly labeled preference alternatives. It keeps genre and rating preferences when possible, and explains when it relaxes year, runtime, vote-count, or genre filters to find more options.

Movie cards in every category can load official YouTube trailers from TMDB inside the app. Open a trailer in an expanded dialog for a larger player. If a trailer is unavailable, the card offers a YouTube search link; TMDB credentials are needed to look up trailers for catalog movies.

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

   `TMDB_API_TOKEN` is also accepted if you use a TMDB read access token. The TMDB integration is optional; the curated catalog and recommendation features work without a credential. You can also enter a key or token in the app's **Configure TMDB API key** panel for the current session.
   After deployment, open **Filters and TMDB settings** and select **Test TMDB** to verify the secret is accepted and live movie data can be loaded.

## Watchlists

No account or sign-in is required. Select **⭐ Watchlist** on any movie card to save it to the current Streamlit session. The list is available across app reruns during that session, but is cleared when the session ends or the page is reloaded; it is not synced across devices.

## Catalog tools

- `python build_dataset.py` regenerates the curated starter catalog.
- `python add_category_movies.py` appends the additional category titles. If `TMDB_API_KEY` is set in the environment or `.env`, it also looks up images and trailers.
- `python enrich_with_tmdb.py` and `python fetch_backdrops.py` optionally enrich catalog artwork using TMDB.

Movies imported through the live TMDB browser are written to the app's local catalog. Streamlit Community Cloud's filesystem is ephemeral, so those imports are not a permanent replacement for updating and pushing the CSV in the GitHub repository.

With `TMDB_API_KEY` configured, use **TMDB Live Discovery → Expand the recommendation catalog with TMDB** to import up to 100 popular titles or 2026 releases at a time. Only titles with posters are added, and existing titles are skipped. Cloud imports are temporary; add desired titles to `data/movies.csv` and push the updated file to keep them across redeployments.
