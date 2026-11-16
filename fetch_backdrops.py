"""Fetch wide backdrop images from TMDB for movies.csv."""
import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")

df = pd.read_csv(CSV_PATH)
if "backdrop_url" not in df.columns:
    df["backdrop_url"] = ""

session = requests.Session()
count = 0
for idx, row in df.iterrows():
    title = row["title"]
    search_title = title.replace(":", "")
    year = int(row["year"]) if pd.notna(row["year"]) else None

    params = {"api_key": API_KEY, "query": search_title, "include_adult": False}
    if year:
        params["year"] = year

    try:
        r = session.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=5)
        if r.status_code == 200:
            res = r.json().get("results", [])
            if res:
                bd_path = res[0].get("backdrop_path")
                if bd_path:
                    df.at[idx, "backdrop_url"] = f"https://image.tmdb.org/t/p/w1280{bd_path}"
                    count += 1
        time.sleep(0.06)
    except Exception as e:
        print(f"Error {title}: {e}")

df.to_csv(CSV_PATH, index=False)
print(f"Updated {count} movies with widescreen TMDB backdrop URLs!")
