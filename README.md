# CineMatch AI

CineMatch is a Streamlit movie-discovery app with a dark cinema theme, content-based recommendations, mood matching, movie blends, watchlists, analytics, and optional live movie data from TMDB. The top search accepts a movie title or a free-text description (for example, “emotional space adventure about family”) and ranks catalog recommendations by their plot, keywords, genre, cast, director, and other metadata. Button-based filters let users choose a minimum rating, release decade, runtime band, minimum vote count, and any combination of genres; these carry through catalog recommendations and movie collections. Collections can also be sorted by rating, votes, release date, or runtime.

Recommendation cards show the catalog's available information. With `TMDB_API_KEY` configured, the app enriches title/year-matched movies with TMDB certification, plot, keywords, cast, director, runtime, rating, vote count, budget, box office, and other movie details. Information TMDB does not provide is left unavailable rather than guessed.

Movie artwork is displayed only from TMDB's image host. Posters on catalog movie cards throughout the app are accepted only when a TMDB result exactly matches both the movie title and release year; otherwise the app shows a neutral placeholder instead of unrelated artwork. Live TMDB feeds use the poster attached to the same TMDB movie record.

Movie collections, recommendation cards, roulette picks, and saved-movie cards omit titles without a verified poster. Connect a TMDB key or read token to display the curated catalog. The Browse tab includes an Upcoming Movies category powered by TMDB, with the same genre, rating, year, runtime, vote, poster, trailer, sorting, and import features as the other live categories.

When direct similar-movie or prompt matches are unavailable, CineMatch offers clearly labeled preference alternatives. It keeps genre and rating preferences when possible, and explains when it relaxes year, runtime, vote-count, or genre filters to find more options.

Movie cards can load official YouTube trailers from TMDB inside the app. If a trailer is unavailable, the card offers a YouTube search link; TMDB credentials are needed to look up trailers for catalog movies.

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

## User accounts and private watchlists

Persistent accounts use Supabase Auth and Postgres. GitHub OAuth and email/password sign-in are available. In Streamlit Community Cloud, add the project URL and public anon key under **App settings → Secrets**:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-public-anon-key"
SUPABASE_REDIRECT_URL = "https://your-app.streamlit.app"
SUPABASE_OAUTH_STATE_SECRET = "a-long-random-secret"
```

Generate a unique `SUPABASE_OAUTH_STATE_SECRET` (for example, with `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Do not use or expose the Supabase `service_role` key; CineMatch rejects it.

To enable GitHub sign-in, create a GitHub OAuth App. Set its authorization callback URL to the callback shown for the GitHub provider in **Supabase → Authentication → Sign In / Providers** (typically `https://<project-ref>.supabase.co/auth/v1/callback`), then enter the GitHub client ID and secret in that Supabase provider's settings. Add the CineMatch app URL and local development URL to **Supabase → Authentication → URL Configuration → Redirect URLs** (for example, `https://your-app.streamlit.app/**` and `http://localhost:8501/**`). The GitHub client secret stays in Supabase and is never added to Streamlit Secrets or the repository.

Enable email/password sign-in in Supabase Authentication if you want to keep that alternative, and configure email delivery if email confirmation is enabled.

Run this SQL in the Supabase SQL Editor to create the private watchlist table and enforce per-user access:

```sql
create table public.user_watchlists (
    user_id uuid not null references auth.users(id) on delete cascade,
    movie_id text not null,
    movie_data jsonb not null,
    created_at timestamptz not null default now(),
    primary key (user_id, movie_id)
);

alter table public.user_watchlists enable row level security;
revoke all on public.user_watchlists from anon;
grant select, insert, update, delete on public.user_watchlists to authenticated;

create policy "Users manage only their own watchlist"
on public.user_watchlists
for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
```

Visitors can browse without an account, but must sign in to save or manage a watchlist. The app uses the user's access token and the database policy for every watchlist request; account passwords are handled by Supabase Auth and are never stored by CineMatch.

For local development, copy `.env.example` to `.env` and set `TMDB_API_KEY`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY` as needed. Keep API credentials out of GitHub: `.env` and Streamlit's `secrets.toml` are excluded by `.gitignore`.

## Catalog tools

- `python build_dataset.py` regenerates the curated starter catalog.
- `python add_category_movies.py` appends the additional category titles. If `TMDB_API_KEY` is set in the environment or `.env`, it also looks up images and trailers.
- `python enrich_with_tmdb.py` and `python fetch_backdrops.py` optionally enrich catalog artwork using TMDB.

Movies imported through the live TMDB browser are written to the app's local catalog. Streamlit Community Cloud's filesystem is ephemeral, so those imports are not a permanent replacement for updating and pushing the CSV in the GitHub repository.

With `TMDB_API_KEY` configured, use **TMDB Live Discovery → Expand the recommendation catalog with TMDB** to import up to 100 popular titles or 2026 releases at a time. Only titles with posters are added, and existing titles are skipped. Cloud imports are temporary; add desired titles to `data/movies.csv` and push the updated file to keep them across redeployments.
