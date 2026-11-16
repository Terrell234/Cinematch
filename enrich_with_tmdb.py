"""Enrich movies.csv with official high-resolution posters and YouTube trailers from TMDB."""
import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")

if not API_KEY:
    print("Error: TMDB_API_KEY not found.")
    exit(1)

df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} movies to enrich from TMDB...")

session = requests.Session()

enriched_count = 0
for idx, row in df.iterrows():
    title = row["title"]
    year = int(row["year"]) if pd.notna(row["year"]) else None

    # Clean title for search (e.g. "Dune: Part One" -> "Dune Part One")
    search_title = title.replace(":", "")

    search_url = f"https://api.themoviedb.org/3/search/movie"
    params = {"api_key": API_KEY, "query": search_title, "include_adult": False}
    if year:
        params["year"] = year

    try:
        r = session.get(search_url, params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                top_match = results[0]
                tmdb_id = top_match.get("id")
                poster_path = top_match.get("poster_path")

                if poster_path:
                    df.at[idx, "poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"

                # Fetch official trailer
                video_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
                vr = session.get(video_url, params={"api_key": API_KEY}, timeout=5)
                if vr.status_code == 200:
                    vdata = vr.json().get("results", [])
                    for v in vdata:
                        if v.get("site") == "YouTube" and v.get("type") in ["Trailer", "Teaser"]:
                            df.at[idx, "trailer_url"] = f"https://www.youtube.com/watch?v={v.get('key')}"
                            break

                enriched_count += 1
                if enriched_count % 15 == 0:
                    print(f"Enriched {enriched_count}/{len(df)} movies...")
        time.sleep(0.08)  # Polite rate limit
    except Exception as e:
        print(f"Error enriching {title}: {e}")

df.to_csv(CSV_PATH, index=False)
print(f"Enrichment complete! Successfully updated {enriched_count} movies with official TMDB posters and trailers.")
