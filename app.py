"""CineMatch AI - Modern Cinema Recommendation Studio.
Featuring cutting-edge streaming UI, vibrant neon aesthetics, widescreen backdrops,
content-based ML, Cinema Blend alchemy, visual mood matching, and live TMDB sync.
"""

import os
import random
from datetime import date
from urllib.parse import urlparse

import requests
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.expanduser("~/.env"))

from src.data_loader import (
    add_movie_to_dataset,
    get_recommender,
    load_movie_data,
)
from src.tmdb_client import TMDBClient

# Page configuration
st.set_page_config(
    page_title="CineMatch AI — Modern Cinema Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom High-End Cinema CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Material+Symbols+Rounded');

    .stApp {
        background: radial-gradient(ellipse at 50% -18%, rgba(180, 111, 63, 0.16), transparent 44%),
                    #0f0d0b;
        color: #f3eadc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .material-symbols-rounded {
        font-family: 'Material Symbols Rounded';
        font-weight: normal;
        font-style: normal;
        font-size: 1.15em;
        line-height: 1;
        display: inline-block;
        vertical-align: middle;
        white-space: nowrap;
        font-feature-settings: 'liga';
    }

    .marquee-hero {
        position: relative;
        background: linear-gradient(110deg, #211b16 0%, #191511 58%, #241710 100%);
        border: 1px solid #3b2b20;
        border-radius: 12px;
        padding: 26px 30px;
        margin-bottom: 24px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.42);
        overflow: hidden;
    }

    .brand-lockup {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        color: #c47a50;
    }

    .brand-lockup .material-symbols-rounded {
        font-size: 1.7rem;
    }

    .marquee-title {
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: 0.11em;
        color: #f3eadc;
    }

    .marquee-title span {
        color: #d39262;
    }

    .marquee-sub {
        font-size: 0.96rem;
        color: #c2b3a2;
        font-weight: 500;
        line-height: 1.5;
        max-width: 900px;
    }

    .billboard-container {
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #46372b;
        margin-bottom: 28px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65);
        background-size: cover;
        background-position: center top;
        min-height: 340px;
    }

    .billboard-overlay {
        background: linear-gradient(90deg, rgba(15, 13, 11, 0.97) 0%, rgba(15, 13, 11, 0.84) 55%, rgba(15, 13, 11, 0.35) 100%);
        padding: 32px 36px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .cinema-card {
        background: #1d1915;
        border: 1px solid #382c22;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 22px;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
        display: flex;
        flex-direction: column;
        position: relative;
    }

    .cinema-card:hover {
        transform: translateY(-3px);
        border-color: rgba(196, 122, 80, 0.78);
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.55), 0 0 20px rgba(196, 122, 80, 0.08);
    }

    .poster-placeholder {
        aspect-ratio: 2 / 3;
        width: 100%;
        border-radius: 7px;
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        color: #b9a895;
        background: linear-gradient(145deg, #302820, #171310);
        border: 1px solid #46372b;
        text-align: center;
    }

    .match-pill {
        display: inline-block;
        background: #b9613f;
        color: #fff8f0;
        font-weight: 800;
        font-size: 0.8rem;
        padding: 4px 12px;
        border-radius: 4px;
        margin-bottom: 10px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .rating-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: #30261b;
        color: #e5bf78;
        border: 1px solid #55432c;
        font-weight: 800;
        font-size: 0.84rem;
        padding: 3px 10px;
        border-radius: 8px;
    }

    .runtime-pill {
        display: inline-block;
        background: #28221b;
        color: #c8b9a7;
        border: 1px solid #40352a;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 8px;
        margin-left: 6px;
    }

    .genre-chip {
        display: inline-block;
        background: #29231d;
        color: #e1d5c6;
        font-size: 0.74rem;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 6px;
        margin-right: 5px;
        margin-bottom: 6px;
        border: 1px solid #40352a;
        transition: all 0.2s;
    }

    .genre-chip:hover {
        background: #393027;
        border-color: #72553e;
    }

    .explanation-badge {
        background: rgba(196, 122, 80, 0.1);
        border-left: 3px solid #c47a50;
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 0.82rem;
        color: #d7c9b9;
        margin-top: 10px;
        margin-bottom: 12px;
        line-height: 1.45;
    }

    .poster-container {
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.5);
    }

    .mood-card {
        background: #1d1915;
        border: 1px solid #382c22;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        transition: all 0.25s;
    }

    div[data-testid="stMetric"] {
        background: #191511;
        border: 1px solid #382c22;
        border-radius: 10px;
        padding: 12px 18px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #191511;
        padding: 6px;
        border-radius: 8px;
        border: 1px solid #382c22;
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 14px;
        font-weight: 600;
        color: #bcae9e;
    }

    .stTabs [aria-selected="true"] {
        background: #a95538 !important;
        color: #fff8f0 !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        background-color: #211b16;
        border-color: #49382a;
        border-radius: 6px;
    }

    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
        transition: background-color 0.18s ease, border-color 0.18s ease;
    }

    .stButton > button[kind="primary"] {
        background: #a95538;
        border-color: #a95538;
    }

    .stButton > button[kind="primary"]:hover {
        background: #87442f;
        border-color: #87442f;
    }

    @media (max-width: 800px) {
        .marquee-hero { padding: 20px; }
        .marquee-title { font-size: 1.3rem; }
        .stTabs [data-baseweb="tab"] { padding: 7px 9px; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []
if "selected_movie_for_search" not in st.session_state:
    st.session_state["selected_movie_for_search"] = "Inception"

try:
    secret_key = str(
        st.secrets.get("TMDB_API_KEY", "")
        or st.secrets.get("TMDB_API_TOKEN", "")
        or ""
    ).strip()
except FileNotFoundError:
    secret_key = ""
env_key = (
    os.environ.get("TMDB_API_KEY", "").strip()
    or os.environ.get("TMDB_API_TOKEN", "").strip()
)
if secret_key or env_key:
    st.session_state["tmdb_api_key"] = secret_key or env_key
elif "tmdb_api_key" not in st.session_state:
    st.session_state["tmdb_api_key"] = ""

# Load data and recommendation engine
try:
    df = load_movie_data()
    recommender = get_recommender()
except Exception as e:
    st.error(f"Error loading movie dataset: {e}")
    st.stop()

# Initialize TMDB Client
tmdb = TMDBClient(api_key_or_token=st.session_state.get("tmdb_api_key", ""))


def show_tmdb_error(action: str, error: requests.RequestException) -> None:
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    reason = f"HTTP {status_code}" if status_code else type(error).__name__
    st.error(f"{action} failed ({reason}). Check the TMDB key and network connection.")


def load_tmdb_runtimes(movies: list[dict]) -> list[dict]:
    """Fetch runtime metadata only when a narrowed runtime filter needs it."""
    if runtime_range_filter == runtime_bounds:
        return movies

    cache = st.session_state["tmdb_runtime_cache"]
    enriched = []
    for item in movies:
        movie = dict(item)
        tmdb_id = movie.get("id")
        if not tmdb_id:
            enriched.append(movie)
            continue
        if tmdb_id not in cache:
            try:
                details = tmdb.get_movie_details(tmdb_id)
            except requests.RequestException as error:
                show_tmdb_error(f"Could not load runtime for {movie.get('title', 'movie')}", error)
                continue
            cache[tmdb_id] = details.get("runtime")
        runtime = cache[tmdb_id]
        if runtime is not None:
            movie["runtime"] = runtime
        enriched.append(movie)
    return enriched


def matches_any_genre(value: str, selected_genres: set[str]) -> bool:
    movie_genres = {genre.strip() for genre in str(value or "").split(",") if genre.strip()}
    return bool(movie_genres.intersection(selected_genres))


def reset_cinema_filters() -> None:
    st.session_state["min_rating"] = 7.0
    st.session_state["genre_filter"] = []
    st.session_state["year_range"] = (min_year, max_year)
    st.session_state["runtime_range"] = runtime_bounds
    st.session_state["min_votes"] = 0


# -------------------------------------------------------------
# TOP-OF-PAGE MOVIE SEARCH
# -------------------------------------------------------------
if "catalog_search" not in st.session_state:
    st.session_state["catalog_search"] = ""
if "catalog_tmdb_poster_cache_v2" not in st.session_state:
    st.session_state["catalog_tmdb_poster_cache_v2"] = {}
if "catalog_tmdb_details_cache" not in st.session_state:
    st.session_state["catalog_tmdb_details_cache"] = {}
if "tmdb_runtime_cache" not in st.session_state:
    st.session_state["tmdb_runtime_cache"] = {}

with st.form("catalog_search_form", border=False):
    search_cols = st.columns([6, 1])
    with search_cols[0]:
        search_input = st.text_input(
            ":material/search: Search the movie catalog",
            placeholder="Describe a story, mood, genre, actor, director, or movie...",
            key="catalog_search_input",
        )
    with search_cols[1]:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        search_submitted = st.form_submit_button(
            "Search",
            icon=":material/search:",
            type="primary",
            use_container_width=True,
        )

if search_submitted:
    st.session_state["catalog_search"] = search_input.strip()
    if search_input.strip() and not tmdb.is_configured:
        st.info("Recommendations use the local catalog. Add a TMDB key to retrieve live movie details.")

search_query = st.session_state["catalog_search"]

# -------------------------------------------------------------
# HERO MARQUEE BANNER
# -------------------------------------------------------------
st.markdown("""
<div class="marquee-hero">
    <div class="brand-lockup"><span class="material-symbols-rounded">movie</span><div class="marquee-title">CINE<span>MATCH</span></div></div>
    <div class="marquee-sub">Settle in, find a favorite, and make movie night feel like home.</div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# TOP SEARCH AND CINEMA FILTERS
# -------------------------------------------------------------
with st.expander("🎛️ Filters and TMDB settings", expanded=True):
    runtime_bounds = (int(df["runtime"].min()), int(df["runtime"].max()))
    filter_cols = st.columns([1, 1.4, 1.6])
    with filter_cols[0]:
        min_rating_filter = st.slider(
            "⭐ Minimum rating",
            min_value=0.0,
            max_value=10.0,
            value=st.session_state.get("min_rating", 7.0),
            step=0.5,
            key="min_rating",
        )

    min_year = int(df["year"].min())
    max_year = max(int(df["year"].max()), date.today().year)
    with filter_cols[1]:
        year_range_filter = st.slider(
            "📅 Release years",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            key="year_range",
        )

    with filter_cols[2]:
        runtime_range_filter = st.slider(
            "⏱️ Runtime (minutes)",
            min_value=runtime_bounds[0],
            max_value=runtime_bounds[1],
            value=st.session_state.get("runtime_range", runtime_bounds),
            step=5,
            key="runtime_range",
        )

    all_genres = recommender.get_all_genres()
    detail_cols = st.columns([2, 1.4, 1, 0.8])
    with detail_cols[0]:
        genre_filters = st.multiselect(
            "🎭 Include genres",
            options=all_genres,
            default=st.session_state.get("genre_filter", []),
            key="genre_filter",
        )

    with detail_cols[1]:
        max_votes = max(1, int(df["votes"].max()))
        min_votes_filter = st.number_input(
            "📊 Minimum votes",
            min_value=0,
            max_value=max_votes,
            value=st.session_state.get("min_votes", 0),
            step=1000,
            key="min_votes",
            help="Raise this to favor movies with a larger audience sample.",
        )

    with detail_cols[2]:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        st.caption(
            f"{runtime_range_filter[0]}–{runtime_range_filter[1]} min · "
            f"{year_range_filter[0]}–{year_range_filter[1]}"
        )

    with detail_cols[3]:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        st.button(
            "Reset",
            use_container_width=True,
            help="Reset cinema filters",
            on_click=reset_cinema_filters,
        )

    tmdb_status = "🟢 TMDB key loaded" if tmdb.is_configured else "⚫ TMDB key not set"
    status_cols = st.columns([4, 1])
    with status_cols[0]:
        st.caption(
            f"{tmdb_status} · {len(df)} movies in catalog · "
            f"{len(st.session_state['watchlist'])} saved"
        )
    with status_cols[1]:
        if st.button("Test TMDB", key="test_tmdb_connection", use_container_width=True):
            if not tmdb.is_configured:
                st.error("Add `TMDB_API_KEY` to Streamlit Secrets to test the connection.")
            else:
                try:
                    with st.spinner("Checking TMDB connection..."):
                        test_results = tmdb.get_trending_movies()
                except requests.RequestException as error:
                    show_tmdb_error("TMDB connection test", error)
                else:
                    st.success(f"Connected to TMDB. Loaded {len(test_results)} trending movies.")

with st.expander("🔑 Configure TMDB API key"):
    tmdb_key_input = st.text_input(
        "API Key / Read Token",
        value=st.session_state["tmdb_api_key"],
        type="password",
        help="For a persistent Streamlit Cloud credential, add TMDB_API_KEY or TMDB_API_TOKEN under app Settings → Secrets.",
    )
    if tmdb_key_input != st.session_state["tmdb_api_key"]:
        st.session_state["tmdb_api_key"] = tmdb_key_input.strip()
        st.rerun()

# Vibrant Metrics Bar
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
m_col1.metric("🍿 Catalog", f"{len(df)} Films")
m_col2.metric("⭐ Top Rated", f"{df.loc[df['rating'].idxmax()]['title']} ({df['rating'].max()})")
m_col3.metric("🎭 Genres", f"{len(all_genres)} Types")
m_col4.metric("⏱️ Avg Runtime", f"{int(df['runtime'].mean())} min")
m_col5.metric("📌 My Watchlist", f"{len(st.session_state['watchlist'])}")

# -------------------------------------------------------------
# COMPONENT: VIBRANT MOVIE CARD
# -------------------------------------------------------------
def is_verified_tmdb_art(url: str) -> bool:
    parsed_url = urlparse(str(url or ""))
    return parsed_url.scheme == "https" and parsed_url.hostname == "image.tmdb.org"


def resolve_catalog_movie_poster(movie: dict) -> dict:
    """Use artwork only after TMDB confirms the catalog title and release year."""
    resolved_movie = dict(movie)
    title = str(resolved_movie.get("title") or "").strip()
    try:
        year = int(resolved_movie.get("year"))
    except (TypeError, ValueError):
        resolved_movie["poster_url"] = ""
        return resolved_movie

    if not title or not tmdb.is_configured:
        resolved_movie["poster_url"] = ""
        return resolved_movie

    title_year = (title.casefold(), year)
    poster_cache = st.session_state["catalog_tmdb_poster_cache_v2"]
    if title_year not in poster_cache:
        try:
            poster_cache[title_year] = tmdb.get_catalog_poster(title, year)
        except requests.RequestException as error:
            poster_cache[title_year] = None
            show_tmdb_error(f"Could not verify the poster for {title}", error)

    matched_movie = poster_cache.get(title_year) or {}
    resolved_movie["poster_url"] = matched_movie.get("poster_url", "")
    return resolved_movie


def render_movie_poster(movie: dict, width: int | None = None) -> None:
    if movie.get("title") and movie.get("year") is not None:
        movie = resolve_catalog_movie_poster(movie)
    poster_url = str(movie.get("poster_url") or "").strip()
    if poster_url and is_verified_tmdb_art(poster_url):
        if width:
            st.image(poster_url, width=width)
        else:
            st.image(poster_url, use_container_width=True)
        return

    placeholder_text = (
        "Connect TMDB to load verified posters"
        if not tmdb.is_configured
        else "No TMDB poster matched this title and year"
    )
    st.markdown(
        f"""
        <div class="poster-placeholder">
            <span class="material-symbols-rounded" style="font-size:2rem;">image_not_supported</span>
            <span>{placeholder_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cinema_card(
    movie: dict,
    key_prefix: str = "card",
    show_match_button: bool = True,
    show_full_details: bool = False,
):
    m_id = movie.get("id", random.randint(1000, 9999))
    title = movie.get("title", "Untitled")
    year = movie.get("year", "N/A")
    rating = movie.get("rating", 7.5)
    runtime = movie.get("runtime", 120)
    runtime_label = f"⏱️ {runtime}m" if runtime else "⏱️ Runtime N/A"
    genres = movie.get("genres", "")
    director = movie.get("director", "Unknown")
    cast = movie.get("cast", "")
    certification = movie.get("certification") or "Not available"
    tagline = movie.get("tagline", "")
    overview = movie.get("overview", "")
    keywords = movie.get("keywords") or "Not available"
    box_office = movie.get("box_office") or "Not available"
    trailer_url = movie.get("trailer_url") or f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+trailer"
    match_pct = movie.get("match_percentage")
    reasons = movie.get("match_reasons", [])

    with st.container():
        st.markdown('<div class="cinema-card">', unsafe_allow_html=True)

        render_movie_poster(movie)

        if match_pct:
            st.markdown(f'<div class="match-pill">🎯 {match_pct}% MATCH</div>', unsafe_allow_html=True)

        st.markdown(f"<h4 style='margin:4px 0 6px 0; font-weight:800; font-size:1.15rem; color:#ffffff;'>{title} <span style='font-size:0.85rem; color:#94a3b8; font-weight:500;'>({year})</span></h4>", unsafe_allow_html=True)

        # Rating & Runtime Pills
        st.markdown(f"""
        <div style="margin-bottom:8px;">
            <span class="rating-pill">⭐ {rating} / 10 · {int(movie.get("votes") or 0):,} votes</span>
            <span class="runtime-pill">{runtime_label}</span>
        </div>
        """, unsafe_allow_html=True)

        # Genre chips
        chips_html = "".join([f'<span class="genre-chip">{g.strip()}</span>' for g in str(genres).split(",")[:3]])
        st.markdown(f"<div style='margin-bottom:6px;'>{chips_html}</div>", unsafe_allow_html=True)

        st.caption(
            f"🎬 **Dir:** {director} • 👥 **Cast:** "
            f"{cast.split(',')[0] if cast else 'Ensemble'} • "
            f"🏷️ **Rating:** {certification}"
        )

        if tagline:
            st.markdown(f"<div style='font-size:0.85rem; color:#f59e0b; font-style:italic; margin-top:2px;'>\"{tagline}\"</div>", unsafe_allow_html=True)

        if reasons:
            reasons_html = " • ".join(reasons[:2])
            st.markdown(f'<div class="explanation-badge">💡 <b>DNA Match:</b> {reasons_html}</div>', unsafe_allow_html=True)

        with st.expander("📖 Synopsis"):
            st.write(overview)

        if show_full_details:
            with st.expander("🎭 Full movie details"):
                st.write(f"**Certification:** {certification}")
                st.write(f"**Director:** {director or 'Not available'}")
                st.write(f"**Full cast:** {cast or 'Not available'}")
                st.write(f"**Keywords:** {keywords}")
                st.write(f"**Box office:** {box_office}")
                budget = int(movie.get("budget") or 0)
                st.write(f"**Budget:** {f'${budget:,}' if budget else 'Not available'}")
                st.write(f"**Status:** {movie.get('status') or 'Not available'}")
                st.write(
                    f"**Original language:** "
                    f"{movie.get('original_language') or 'Not available'}"
                )

        with st.expander("▶️ Watch Trailer"):
            if "youtube.com" in trailer_url or "youtu.be" in trailer_url:
                st.video(trailer_url)
            else:
                st.link_button("Watch Trailer on YouTube", trailer_url, use_container_width=True)

        # Action Buttons Row
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            is_saved = any(item["title"].lower() == title.lower() for item in st.session_state["watchlist"])
            if is_saved:
                if st.button("✅ Saved", key=f"unsave_{key_prefix}_{m_id}", use_container_width=True):
                    st.session_state["watchlist"] = [item for item in st.session_state["watchlist"] if item["title"].lower() != title.lower()]
                    st.toast(f"Removed '{title}' from Watchlist.")
                    st.rerun()
            else:
                if st.button("⭐ Watchlist", key=f"save_{key_prefix}_{m_id}", use_container_width=True):
                    st.session_state["watchlist"].append(movie)
                    st.toast(f"Added '{title}' to Watchlist! ⭐")
                    st.rerun()

        with b_col2:
            if show_match_button:
                if st.button("🔍 Match This", key=f"match_seed_{key_prefix}_{m_id}", use_container_width=True, help="Set as focus movie"):
                    st.session_state["selected_movie_for_search"] = title
                    st.toast(f"Switched focus to '{title}'! 🎯")
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# CATEGORY DEFINITIONS
# -------------------------------------------------------------
CATEGORIES = {
    "🌸 Anime": {
        "desc": "Legendary Japanese animation, Studio Ghibli wonders, cyberpunk epics, and heartfelt visual tales.",
        "filter": lambda d: d[d["genres"].str.contains("Animation", na=False) | d["keywords"].str.contains("anime", case=False, na=False)],
        "color": "linear-gradient(135deg, #30251d 0%, #1c1713 100%)",
        "tmdb_key": "anime"
    },
    "🔥 New Releases": {
        "desc": "The newest theatrical blockbusters and contemporary cinema sensations (2022 to 2024+).",
        "filter": lambda d: d[d["year"] >= 2022].sort_values(by="year", ascending=False),
        "color": "linear-gradient(135deg, #332319 0%, #1c1713 100%)",
        "tmdb_key": "new"
    },
    "🎭 Drama": {
        "desc": "Compelling character studies, psychological thrillers, and award-winning emotional masterworks.",
        "filter": lambda d: d[d["genres"].str.contains("Drama", na=False)].sort_values(by="rating", ascending=False),
        "color": "linear-gradient(135deg, #30231c 0%, #1c1713 100%)",
        "tmdb_key": "drama"
    },
    "💥 Action & Adventure": {
        "desc": "Heart-pounding stunts, cosmic odysseys, mythical quests, and electrifying cinema spectacles.",
        "filter": lambda d: d[d["genres"].str.contains("Action|Adventure", na=False)].sort_values(by="rating", ascending=False),
        "color": "linear-gradient(135deg, #35251a 0%, #1c1713 100%)",
        "tmdb_key": "action"
    },
    "🏛️ History Shows & Sagas": {
        "desc": "True-to-life historic epochs, epic war chronicles, and critically acclaimed historical mini-series.",
        "filter": lambda d: d[d["genres"].str.contains("History|War", na=False) | d["keywords"].str.contains("history|world war|chernobyl", case=False, na=False)].sort_values(by="rating", ascending=False),
        "color": "linear-gradient(135deg, #2b261c 0%, #1c1713 100%)",
        "tmdb_key": "history"
    },
    "💖 Romance": {
        "desc": "Timeless love stories, poetic encounters, bittersweet connections, and soulful journeys of the heart.",
        "filter": lambda d: d[d["genres"].str.contains("Romance", na=False)].sort_values(by="rating", ascending=False),
        "color": "linear-gradient(135deg, #38251e 0%, #1c1713 100%)",
        "tmdb_key": "romance"
    },
    "👑 Most Popular": {
        "desc": "The highest-voted, widely celebrated, and universally acclaimed cinema masterpieces in history.",
        "filter": lambda d: d.sort_values(by="votes", ascending=False),
        "color": "linear-gradient(135deg, #352718 0%, #1c1713 100%)",
        "tmdb_key": "popular"
    }
}

# -------------------------------------------------------------
# GLOBAL CATALOG SEARCH
# -------------------------------------------------------------
if search_query.strip():
    st.markdown(f"### 🎬 Movies related to “{search_query.strip()}”")
    min_prompt_relevance = st.slider(
        "Minimum prompt relevance",
        min_value=0,
        max_value=50,
        value=5,
        step=1,
        help="Raise this to hide weaker matches; lower it to show more recommendations.",
        key="prompt_relevance_filter",
    )
    recommendations = recommender.recommend_for_prompt(
        prompt=search_query,
        top_n=12,
        genre_filter=genre_filters or None,
        min_rating=min_rating_filter,
        year_range=year_range_filter,
        max_runtime=runtime_range_filter[1],
        min_relevance=min_prompt_relevance,
        min_runtime=runtime_range_filter[0],
        min_votes=min_votes_filter,
    )
    search_results = pd.DataFrame(recommendations)
    poster_cache = st.session_state["catalog_tmdb_poster_cache_v2"]
    details_cache = st.session_state["catalog_tmdb_details_cache"]

    if tmdb.is_configured:
        for movie in search_results.to_dict(orient="records"):
            title_year = (str(movie["title"]).casefold(), int(movie["year"]))
            if title_year not in poster_cache:
                try:
                    poster_cache[title_year] = tmdb.get_catalog_poster(
                        str(movie["title"]),
                        int(movie["year"]),
                    )
                except requests.RequestException as error:
                    poster_cache[title_year] = None
                    show_tmdb_error(f"Could not load poster for {movie['title']}", error)

            tmdb_match = poster_cache.get(title_year)
            movie_id = tmdb_match.get("tmdb_id") if tmdb_match else None
            if movie_id and movie_id not in details_cache:
                try:
                    details = tmdb.get_movie_details(movie_id)
                except requests.RequestException as error:
                    details_cache[movie_id] = None
                    show_tmdb_error(f"Could not load details for {movie['title']}", error)
                else:
                    details_cache[movie_id] = tmdb.format_tmdb_movie(details)

    if search_results.empty:
        st.info(
            "No recommendations meet the prompt and active filters. "
            "Lower the minimum relevance or try describing a genre, mood, story, "
            "actor, director, or movie title."
        )
    else:
        st.caption(
            f"Top {len(search_results)} recommendations ranked by story, genre, "
            "cast, keywords, and other movie details."
        )
        search_cols = st.columns(3)
        detail_fields = (
            "certification",
            "genres",
            "director",
            "cast",
            "rating",
            "votes",
            "runtime",
            "tagline",
            "overview",
            "keywords",
            "box_office",
            "budget",
            "revenue",
            "status",
            "original_language",
        )
        for index, (_, movie_row) in enumerate(search_results.iterrows()):
            with search_cols[index % 3]:
                movie = movie_row.to_dict()
                title_year = (str(movie["title"]).casefold(), int(movie["year"]))
                tmdb_match = poster_cache.get(title_year)
                if tmdb_match:
                    for field in detail_fields:
                        value = tmdb_match.get(field)
                        if value not in (None, "", 0):
                            movie[field] = value
                    tmdb_id = tmdb_match.get("tmdb_id")
                    tmdb_details = details_cache.get(tmdb_id) if tmdb_id else None
                    if tmdb_details:
                        for field in detail_fields:
                            value = tmdb_details.get(field)
                            if value not in (None, "", 0):
                                movie[field] = value
                    movie["poster_url"] = (
                        (tmdb_details or {}).get("poster_url")
                        or tmdb_match.get("poster_url")
                        or ""
                    )
                    movie["backdrop_url"] = (
                        (tmdb_details or {}).get("backdrop_url")
                        or tmdb_match.get("backdrop_url")
                        or ""
                    )
                else:
                    movie["poster_url"] = ""
                render_cinema_card(
                    movie,
                    key_prefix=f"catalog_search_{index}",
                    show_full_details=True,
                )

# -------------------------------------------------------------
# MAIN APP TABS
# -------------------------------------------------------------
tab_cats, tab_match, tab_blend, tab_mood, tab_roulette, tab_tmdb, tab_watchlist, tab_analytics = st.tabs([
    ":material/movie: Browse",
    ":material/auto_awesome: Matcher",
    ":material/blend: Blend",
    ":material/mood: Mood",
    ":material/casino: Roulette",
    ":material/travel_explore: TMDB",
    f":material/bookmark: Watchlist ({len(st.session_state['watchlist'])})",
    ":material/analytics: Insights"
])


# =============================================================
# TAB 0: CINEMA CATEGORIES & CHANNELS
# =============================================================
with tab_cats:
    st.subheader("🎞️ Browse the collection")
    st.write("Choose a collection, tune the filters above, and sort the results to fit your movie night.")

    cat_keys = list(CATEGORIES.keys())
    current_category = st.session_state.get("active_category", cat_keys[0])
    selected_category_index = cat_keys.index(current_category) if current_category in cat_keys else 0
    active_cat = st.selectbox(
        "Collection",
        options=cat_keys,
        index=selected_category_index,
        key="active_category",
        label_visibility="collapsed",
    )

    active_cat_data = CATEGORIES[active_cat]

    # Glowing Category Banner
    st.markdown(f"""
    <div style="background: {active_cat_data['color']}; border-radius: 16px; padding: 20px 26px; margin: 18px 0; box-shadow: 0 8px 32px rgba(0,0,0,0.4); color: white;">
        <h2 style="margin:0; font-family:'Cabinet Grotesk', sans-serif; font-size:2rem; font-weight:900; text-shadow: 0 2px 8px rgba(0,0,0,0.4);">{active_cat}</h2>
        <div style="font-size:1.02rem; opacity:0.95; margin-top:4px; font-weight:500;">{active_cat_data['desc']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Mode Selector: Curated vs Live TMDB
    col_mode1, col_mode2 = st.columns([2, 1])
    with col_mode1:
        feed_mode = st.radio(
            "Channel Source:",
            options=["🎬 Curated HD Collection", "🌐 Live TMDB Streaming Feed"],
            horizontal=True,
            key=f"feed_mode_{active_cat}"
        )
    with col_mode2:
        category_sort = st.selectbox(
            "Sort collection",
            options=[
                "Collection order",
                "Top rated",
                "Most votes",
                "Newest",
                "Oldest",
                "Shortest runtime",
                "Longest runtime",
            ],
            key=f"category_sort_{active_cat}",
        )

    if feed_mode == "🎬 Curated HD Collection":
        cat_df = active_cat_data["filter"](df)

        cat_df = cat_df[
            (cat_df["rating"] >= min_rating_filter)
            & cat_df["year"].between(*year_range_filter)
            & cat_df["runtime"].between(*runtime_range_filter)
            & (cat_df["votes"] >= min_votes_filter)
        ]
        if genre_filters:
            selected_genres = set(genre_filters)
            cat_df = cat_df[
                cat_df["genres"].apply(lambda value: matches_any_genre(value, selected_genres))
            ]

        catalog_sort_columns = {
            "Top rated": ("rating", False),
            "Most votes": ("votes", False),
            "Newest": ("year", False),
            "Oldest": ("year", True),
            "Shortest runtime": ("runtime", True),
            "Longest runtime": ("runtime", False),
        }
        if category_sort in catalog_sort_columns:
            sort_column, ascending = catalog_sort_columns[category_sort]
            cat_df = cat_df.sort_values(sort_column, ascending=ascending)

        st.caption(f"Showing **{len(cat_df)}** films in {active_cat} after applying your filters.")
        if cat_df.empty:
            st.warning("No films match these filters. Try widening the year or runtime range, lowering the rating/vote minimum, or removing a genre.")
        else:
            cols = st.columns(3)
            for idx, (_, movie_row) in enumerate(cat_df.iterrows()):
                with cols[idx % 3]:
                    render_cinema_card(movie_row.to_dict(), key_prefix=f"cat_{idx}", show_match_button=True)
    else:
        # Live TMDB Stream
        with st.spinner(f"Pulling live {active_cat} feed from TMDB..."):
            tmdb_cat_results = tmdb.get_category_feed(active_cat_data["tmdb_key"])

        tmdb_cat_results = load_tmdb_runtimes(tmdb_cat_results)
        selected_genre_ids = (
            tmdb.genre_ids_for_names(genre_filters) if genre_filters else None
        )
        runtime_filter = (
            None if runtime_range_filter == runtime_bounds else runtime_range_filter
        )
        filtered_category_results = tmdb.filter_movie_results(
            tmdb_cat_results,
            genre_ids=selected_genre_ids,
            min_rating=min_rating_filter,
            year_range=year_range_filter,
            runtime_range=runtime_filter,
            min_votes=min_votes_filter,
        )
        tmdb_sort_columns = {
            "Top rated": ("vote_average", False),
            "Most votes": ("vote_count", False),
            "Newest": ("release_date", False),
            "Oldest": ("release_date", True),
            "Shortest runtime": ("runtime", True),
            "Longest runtime": ("runtime", False),
        }
        if category_sort in tmdb_sort_columns:
            sort_column, ascending = tmdb_sort_columns[category_sort]
            filtered_category_results = sorted(
                filtered_category_results,
                key=lambda item: item.get(sort_column) or 0,
                reverse=not ascending,
            )

        if not tmdb_cat_results:
            st.warning("Could not fetch live TMDB feed. Check your connection or explore the Curated HD Collection!")
        elif not filtered_category_results:
            st.warning("No live titles match these filters. Try widening the year or runtime range, lowering the rating/vote minimum, or removing a genre.")
        else:
            st.caption(
                f"Showing **{len(filtered_category_results)} of {len(tmdb_cat_results)}** "
                "live TMDB titles after applying your filters."
            )
            t_cols = st.columns(3)
            for idx, item in enumerate(filtered_category_results[:15]):
                with t_cols[idx % 3]:
                    tmdb_id = item.get("id")
                    title = item.get("title") or item.get("name") or "Unknown"
                    rel_date = item.get("release_date", "2024")
                    year = rel_date[:4] if rel_date else "2024"
                    vote_avg = round(float(item.get("vote_average", 0.0)), 1)
                    poster_p = item.get("poster_path")
                    p_url = f"https://image.tmdb.org/t/p/w500{poster_p}" if poster_p else ""

                    st.markdown('<div class="cinema-card">', unsafe_allow_html=True)
                    render_movie_poster({"poster_url": p_url})
                    st.markdown(f"#### {title} <span style='font-size:0.85rem; color:#94a3b8;'>({year})</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='rating-pill'>⭐ {vote_avg} / 10</span>", unsafe_allow_html=True)
                    st.caption(item.get("overview", "")[:120] + "...")

                    already_in = title.lower() in [t.lower() for t in df["title"].tolist()]
                    if already_in:
                        st.info("✅ In Local Catalog")
                    else:
                        if st.button(f"📥 Import to CineMatch", key=f"import_cat_{tmdb_id}", use_container_width=True):
                            with st.spinner(f"Pulling details for '{title}'..."):
                                detailed = tmdb.get_movie_details(tmdb_id)
                                formatted = tmdb.format_tmdb_movie(detailed or item)
                                if detailed and detailed.get("backdrop_path"):
                                    formatted["backdrop_url"] = f"https://image.tmdb.org/t/p/w1280{detailed['backdrop_path']}"
                                added = add_movie_to_dataset(formatted)
                                if added:
                                    st.toast(f"Imported '{title}' to catalog! 🎬")
                                    st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================
# TAB 1: SIMILAR MOVIE MATCHER (Content-Based)
# =============================================================
with tab_match:
    st.subheader("🎯 Content-Based Movie Matcher")
    st.write("Select a seed film to discover kindred cinema based on semantic plot depth, director style, mood, and genre weights.")

    all_titles = sorted(df["title"].tolist())

    # Vibrant Visual Quick-Picks Carousel
    st.markdown("#### ⚡ **Popular Movie Seeds (Click to inspect):**")
    visual_seeds = [
        ("Inception", "🌀 Inception"),
        ("Interstellar", "🌌 Interstellar"),
        ("The Dark Knight", "🦇 Dark Knight"),
        ("Pulp Fiction", "🥩 Pulp Fiction"),
        ("Parasite", "🍜 Parasite"),
        ("Dune: Part One", "🏜️ Dune"),
        ("Spirited Away", "🐉 Spirited Away"),
        ("The Matrix", "🕶️ The Matrix")
    ]

    p_cols = st.columns(len(visual_seeds))
    for idx, (f_title, label) in enumerate(visual_seeds):
        with p_cols[idx]:
            film_row = df[df["title"] == f_title]
            if not film_row.empty:
                render_movie_poster(film_row.iloc[0].to_dict())
            if st.button(label, key=f"v_seed_{idx}", use_container_width=True):
                st.session_state["selected_movie_for_search"] = f_title
                st.rerun()

    # Seed Selector Dropdown
    current_selected = st.session_state.get("selected_movie_for_search", "Inception")
    default_idx = all_titles.index(current_selected) if current_selected in all_titles else 0

    c_sel, c_num = st.columns([3, 1])
    with c_sel:
        selected_movie_title = st.selectbox(
            "Search or Select Movie from Catalog:",
            options=all_titles,
            index=default_idx
        )
    with c_num:
        top_n = st.slider("Recommendations Count:", min_value=3, max_value=12, value=6, step=3)

    if selected_movie_title:
        source_movie = recommender.get_movie_by_title(selected_movie_title)
        backdrop_candidate = source_movie.get("backdrop_url") or source_movie.get("poster_url")
        backdrop = backdrop_candidate if is_verified_tmdb_art(backdrop_candidate) else ""

        # WIDESCREEN CINEMA BILLBOARD
        st.markdown(f"""
        <div class="billboard-container" style="background-image: url('{backdrop}');">
            <div class="billboard-overlay">
                <span class="match-pill">FEATURED SEED FILM</span>
                <h1 style="color:#ffffff; font-family:'Cabinet Grotesk', sans-serif; font-size:2.6rem; font-weight:900; margin:4px 0 10px 0;">{source_movie['title']} <span style="font-size:1.4rem; color:#94a3b8;">({source_movie['year']})</span></h1>
                <div style="margin-bottom:12px;">
                    <span class="rating-pill">⭐ {source_movie['rating']} / 10</span>
                    <span class="runtime-pill">⏱️ {source_movie['runtime']} min</span>
                    <span style="color:#e2e8f0; font-size:0.9rem; margin-left:10px;">🎬 <b>Director:</b> {source_movie['director']}</span>
                </div>
                <div style="font-size:1.05rem; color:#ffd000; font-style:italic; margin-bottom:10px;">"{source_movie.get('tagline', '')}"</div>
                <p style="color:#cbd5e1; max-width:850px; font-size:0.98rem; line-height:1.6; margin-bottom:14px;">{source_movie['overview']}</p>
                <div style="color:#94a3b8; font-size:0.88rem;">👥 <b>Cast:</b> {source_movie['cast']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("▶️ Watch Official Trailer for Selected Film"):
            st.video(source_movie.get("trailer_url") or "")

        st.markdown("---")
        st.markdown(f"### 🍿 **Top Kinship Matches for *{selected_movie_title}***")

        recs = recommender.recommend_similar(
            title=selected_movie_title,
            top_n=top_n,
            genre_filter=genre_filters if genre_filters else None,
            min_rating=min_rating_filter,
            year_range=year_range_filter,
            max_runtime=runtime_range_filter[1],
            min_runtime=runtime_range_filter[0],
            min_votes=min_votes_filter,
        )

        if not recs:
            st.warning("No matches with current filters. Try relaxing filters in the sidebar!")
        else:
            cols = st.columns(3)
            for idx, movie in enumerate(recs):
                with cols[idx % 3]:
                    render_cinema_card(movie, key_prefix=f"match_{idx}", show_match_button=True)


# =============================================================
# TAB 2: CINEMA BLEND (Multi-Movie Centroid)
# =============================================================
with tab_blend:
    st.subheader("🧪 Cinema Blend Studio: Hybrid Movie Alchemy")
    st.write("Synthesize a custom recommendation at the exact semantic centroid of two or three movies!")

    st.markdown("#### ⚡ **1-Click Famous Cinema Fusions:**")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        if st.button("🌌 Interstellar + 2001 Space", use_container_width=True):
            st.session_state["blend_1"] = "Interstellar"
            st.session_state["blend_2"] = "2001: A Space Odyssey"
            st.rerun()
    with f2:
        if st.button("🤖 Matrix + Blade Runner 2049", use_container_width=True):
            st.session_state["blend_1"] = "The Matrix"
            st.session_state["blend_2"] = "Blade Runner 2049"
            st.rerun()
    with f3:
        if st.button("🩸 Pulp Fiction + Fight Club", use_container_width=True):
            st.session_state["blend_1"] = "Pulp Fiction"
            st.session_state["blend_2"] = "Fight Club"
            st.rerun()
    with f4:
        if st.button("🌸 Spirited Away + Amélie", use_container_width=True):
            st.session_state["blend_1"] = "Spirited Away"
            st.session_state["blend_2"] = "Amélie"
            st.rerun()

    st.markdown("---")
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        cur_b1 = st.session_state.get("blend_1", "Inception")
        idx_b1 = all_titles.index(cur_b1) if cur_b1 in all_titles else 0
        blend_movie_1 = st.selectbox("Film #1:", options=all_titles, index=idx_b1, key="sb_b1")
        m1_data = recommender.get_movie_by_title(blend_movie_1)
        if m1_data is not None:
            render_movie_poster(m1_data, width=200)

    with b_col2:
        cur_b2 = st.session_state.get("blend_2", "Blade Runner 2049")
        idx_b2 = all_titles.index(cur_b2) if cur_b2 in all_titles else 1
        blend_movie_2 = st.selectbox("Film #2:", options=all_titles, index=idx_b2, key="sb_b2")
        m2_data = recommender.get_movie_by_title(blend_movie_2)
        if m2_data is not None:
            render_movie_poster(m2_data, width=200)

    include_third = st.checkbox("➕ Add a 3rd Film to the Blend?")
    blend_titles = [blend_movie_1, blend_movie_2]
    if include_third:
        blend_movie_3 = st.selectbox("Film #3:", options=all_titles, index=2, key="sb_b3")
        blend_titles.append(blend_movie_3)

    if st.button("🧪 Synthesize Cinema Blend", type="primary", use_container_width=True):
        with st.spinner("Calculating semantic centroid and blending cinematic DNA..."):
            blend_recs = recommender.recommend_cinema_blend(
                titles=blend_titles,
                top_n=6,
                genre_filter=genre_filters if genre_filters else None,
                min_rating=min_rating_filter,
                year_range=year_range_filter,
                max_runtime=runtime_range_filter[1],
                min_runtime=runtime_range_filter[0],
                min_votes=min_votes_filter,
            )

            if not blend_recs:
                st.warning("No blend candidates found with current filters. Try relaxing sidebar filters!")
            else:
                st.success(f"✨ Successfully Synthesized: **{' + '.join(blend_titles)}**!")
                cols = st.columns(3)
                for idx, movie in enumerate(blend_recs):
                    with cols[idx % 3]:
                        render_cinema_card(movie, key_prefix=f"blend_{idx}")


# =============================================================
# TAB 3: MOOD & VIBE MATCHER
# =============================================================
with tab_mood:
    st.subheader("🎭 Emotional Vibe & Mood Matcher")
    st.write("Tune CineMatch to your current headspace with vibrant emotion presets:")

    # Vibrant Visual Mood Grid
    vm1, vm2, vm3, vm4 = st.columns(4)
    with vm1:
        if st.button("🧠 Mind-Bending\n(Twisted & Cerebral)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Mind-Bending", "Psychological"]
            st.rerun()
    with vm2:
        if st.button("💥 Adrenaline Rush\n(Action & High Stakes)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Adrenaline Rush", "Thrilling"]
            st.rerun()
    with vm3:
        if st.button("😭 Tearjerker\n(Deeply Emotional)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Tearjerker", "Emotional"]
            st.rerun()
    with vm4:
        if st.button("✨ Feel-Good & Cozy\n(Warm & Uplifting)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Feel-Good", "Whimsical"]
            st.rerun()

    vm5, vm6, vm7, vm8 = st.columns(4)
    with vm5:
        if st.button("😱 Spine-Chilling\n(Dread & Tension)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Spine-Chilling", "Terrifying"]
            st.rerun()
    with vm6:
        if st.button("🎨 Visually Stunning\n(Epic Cinematography)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Visually Stunning", "Epic"]
            st.rerun()
    with vm7:
        if st.button("🕵️ Intrigue & Mystery\n(Clever Whodunnit)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Witty", "Whodunnit"]
            st.rerun()
    with vm8:
        if st.button("🏆 Masterpiece Classics\n(Cinema Royalty)", use_container_width=True):
            st.session_state["chosen_moods"] = ["Masterpiece", "Iconic"]
            st.rerun()

    all_moods = recommender.get_all_moods()
    default_moods = st.session_state.get("chosen_moods", ["Mind-Bending", "Visionary"])

    selected_mood_tags = st.multiselect(
        "Active Mood Tags:",
        options=all_moods,
        default=[m for m in default_moods if m in all_moods]
    )

    if selected_mood_tags:
        vibe_recs = recommender.recommend_by_mood_and_vibes(
            selected_moods=selected_mood_tags,
            preferred_genres=genre_filters if genre_filters else None,
            min_rating=min_rating_filter,
            year_range=year_range_filter,
            max_runtime=runtime_range_filter[1],
            min_runtime=runtime_range_filter[0],
            min_votes=min_votes_filter,
            top_n=6
        )

        st.markdown(f"#### 🌌 **Curated Films Matching: *{', '.join(selected_mood_tags)}***")
        cols = st.columns(3)
        for idx, movie in enumerate(vibe_recs):
            with cols[idx % 3]:
                render_cinema_card(movie, key_prefix=f"vibe_{idx}")


# =============================================================
# TAB 4: MOVIE ROULETTE / SURPRISE ME
# =============================================================
with tab_roulette:
    st.subheader("🎲 Neon Movie Roulette")
    st.write("Eliminate choice fatigue! Spin the cinema wheel to let algorithm fate pick tonight's film.")

    rc1, rc2 = st.columns([3, 1])
    with rc1:
        roulette_genre = st.selectbox("Genre constraint:", options=["Any Genre"] + all_genres)
    with rc2:
        st.write("")
        st.write("")
        spin_btn = st.button("🎰 SPIN THE WHEEL!", type="primary", use_container_width=True)

    if spin_btn:
        candidates = df.copy()
        candidates = candidates[
            (candidates["rating"] >= min_rating_filter)
            & candidates["year"].between(*year_range_filter)
            & candidates["runtime"].between(*runtime_range_filter)
            & (candidates["votes"] >= min_votes_filter)
        ]
        selected_genres = set(genre_filters)
        if roulette_genre != "Any Genre":
            selected_genres.add(roulette_genre)
        if selected_genres:
            candidates = candidates[
                candidates["genres"].apply(
                    lambda value: matches_any_genre(value, selected_genres)
                )
            ]

        if candidates.empty:
            st.error("No movies found with those strict constraints! Try relaxing filters in the sidebar.")
        else:
            chosen = candidates.sample(1).iloc[0].to_dict()
            st.balloons()
            st.success(f"🎉 Destined for Tonight: **{chosen['title']}** ({chosen['year']})!")

            bd_candidate = chosen.get("backdrop_url") or chosen.get("poster_url")
            bd_url = bd_candidate if is_verified_tmdb_art(bd_candidate) else ""
            st.markdown(f"""
            <div class="billboard-container" style="background-image: url('{bd_url}');">
                <div class="billboard-overlay">
                    <span class="match-pill">ROULETTE SELECTION</span>
                    <h1 style="color:#ffffff; font-family:'Cabinet Grotesk', sans-serif; font-size:2.4rem; font-weight:900; margin:4px 0 10px 0;">{chosen['title']} <span style="font-size:1.3rem; color:#94a3b8;">({chosen['year']})</span></h1>
                    <div style="margin-bottom:12px;">
                        <span class="rating-pill">⭐ {chosen['rating']} / 10</span>
                        <span class="runtime-pill">⏱️ {chosen['runtime']} min</span>
                        <span style="color:#e2e8f0; font-size:0.9rem; margin-left:10px;">🎬 <b>Director:</b> {chosen['director']}</span>
                    </div>
                    <div style="font-size:1.05rem; color:#ffd000; font-style:italic; margin-bottom:8px;">"{chosen.get('tagline', '')}"</div>
                    <p style="color:#cbd5e1; max-width:850px; font-size:0.98rem; line-height:1.5;">{chosen['overview']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("▶️ Watch Official Trailer Right Here", expanded=True):
                st.video(chosen.get("trailer_url") or "")

            b_save, b_spin = st.columns(2)
            with b_save:
                if st.button("⭐ Add to Watchlist", key="roulette_save_btn", use_container_width=True):
                    st.session_state["watchlist"].append(chosen)
                    st.toast("Saved to Watchlist! ⭐")
                    st.rerun()
            with b_spin:
                if st.button("🔄 Spin Again", key="roulette_spin_again", use_container_width=True):
                    st.rerun()


# =============================================================
# TAB 5: TMDB LIVE DISCOVERY & IMPORT
# =============================================================
with tab_tmdb:
    st.subheader("🌐 TMDB Live Discovery & Global Importer")
    st.write("Browse TMDB releases, find movies recommended from a favorite, or search the global catalog.")

    tmdb_mode = st.radio(
        "Choose Live TMDB Feed:",
        options=[
            "🔥 Trending This Week",
            "🎬 Now Playing in Theaters",
            "⭐ All-Time Top Rated",
            "🎯 Recommendations for a Movie",
            "🔍 Search TMDB Global Library",
        ],
        horizontal=True
    )

    if not tmdb.is_configured:
        st.info("Add `TMDB_API_KEY` in Streamlit Cloud Settings → Secrets to expand the catalog with TMDB movies.")
    else:
        with st.expander("📈 Expand the recommendation catalog with TMDB", expanded=True):
            st.write(
                "Import popular TMDB movies into the local catalog so they become available "
                "in the movie matcher, filters, and watchlist recommendations."
            )
            import_col, action_col = st.columns([1, 2])
            with import_col:
                import_count = st.selectbox(
                    "Movies to add (maximum)",
                    options=[20, 40, 60, 100],
                    index=3,
                    key="tmdb_import_count",
                )
            with action_col:
                st.caption(
                    f"Current catalog: **{len(df)}** movies. Already-listed titles are skipped."
                )
                if st.button(
                    f"Add up to {import_count} popular movies",
                    type="primary",
                    key="tmdb_bulk_import",
                ):
                    new_movies = []
                    known_titles = set(df["title"].str.casefold())
                    max_pages = (import_count // 20) * 2
                    try:
                        with st.spinner("Loading popular movies from TMDB..."):
                            for page in range(1, max_pages + 1):
                                page_movies = tmdb.get_popular_movies(page=page)
                                if not page_movies:
                                    break
                                for item in page_movies:
                                    formatted = tmdb.format_tmdb_movie(item)
                                    title = formatted["title"].strip()
                                    if title.casefold() in known_titles:
                                        continue
                                    known_titles.add(title.casefold())
                                    new_movies.append(formatted)
                                    if len(new_movies) >= import_count:
                                        break
                                if len(new_movies) >= import_count:
                                    break
                            added_count = sum(
                                add_movie_to_dataset(movie) for movie in new_movies
                            )
                        if added_count:
                            st.success(
                                f"Added {added_count} movies. The catalog now has "
                                f"{len(df) + added_count} titles."
                            )
                            st.rerun()
                        st.info(
                            "TMDB returned no new titles for this import. Try again later."
                        )
                    except requests.RequestException as error:
                        show_tmdb_error("Could not expand the catalog from TMDB", error)

    tmdb_results = []
    if tmdb_mode == "🎯 Recommendations for a Movie":
        with st.form("tmdb_recommendation_search"):
            recommendation_query = st.text_input(
                "Find a movie to use as your starting point:",
                placeholder="e.g. Inception, Dune, Parasite",
            )
            search_submitted = st.form_submit_button("Search TMDB")

        if search_submitted:
            if not recommendation_query.strip():
                st.session_state["tmdb_recommendation_seeds"] = []
            else:
                st.session_state["tmdb_recommendation_seeds"] = []
                try:
                    with st.spinner("Searching TMDB..."):
                        st.session_state["tmdb_recommendation_seeds"] = tmdb.search_movies(
                            recommendation_query
                        )
                except requests.RequestException as error:
                    show_tmdb_error("TMDB movie search", error)

        recommendation_seeds = st.session_state.get("tmdb_recommendation_seeds", [])
        if recommendation_seeds:
            seed_index = st.selectbox(
                "Choose the movie you like:",
                options=range(len(recommendation_seeds)),
                format_func=lambda index: (
                    f"{recommendation_seeds[index].get('title', 'Untitled')} "
                    f"({(recommendation_seeds[index].get('release_date') or '????')[:4]})"
                ),
                key="tmdb_recommendation_seed",
            )
            seed_movie = recommendation_seeds[seed_index]
            try:
                with st.spinner("Finding movies recommended by TMDB..."):
                    tmdb_results = tmdb.get_movie_recommendations(seed_movie["id"])
            except requests.RequestException as error:
                show_tmdb_error("TMDB recommendations could not be loaded", error)
            st.caption(f"Recommendations based on **{seed_movie.get('title', 'your movie')}**.")
        elif search_submitted and recommendation_query.strip():
            st.info("TMDB did not find a matching movie. Try another title.")
    else:
        try:
            with st.spinner("Connecting to TMDB..."):
                if tmdb_mode == "🔥 Trending This Week":
                    tmdb_results = tmdb.get_trending_movies(time_window="week")
                elif tmdb_mode == "🎬 Now Playing in Theaters":
                    tmdb_results = tmdb.get_now_playing(page=1)
                elif tmdb_mode == "⭐ All-Time Top Rated":
                    tmdb_results = tmdb.get_top_rated(page=1)
                elif tmdb_mode == "🔍 Search TMDB Global Library":
                    search_query = st.text_input(
                        "Enter Movie Name:",
                        placeholder="e.g. Gladiator II, Challengers, Dune 2, Nosferatu...",
                    )
                    if search_query:
                        tmdb_results = tmdb.search_movies(search_query)
        except requests.RequestException as error:
            show_tmdb_error("TMDB request", error)

    if tmdb_results:
        tmdb_results = load_tmdb_runtimes(tmdb_results)
        selected_genre_ids = (
            tmdb.genre_ids_for_names(genre_filters) if genre_filters else None
        )
        filtered_results = tmdb.filter_movie_results(
            tmdb_results,
            genre_ids=selected_genre_ids,
            min_rating=min_rating_filter,
            year_range=year_range_filter,
            runtime_range=(
                None if runtime_range_filter == runtime_bounds else runtime_range_filter
            ),
            min_votes=min_votes_filter,
        )
        st.markdown(
            f"Showing **{len(filtered_results)} of {len(tmdb_results)}** TMDB movies "
            "after applying your filters."
        )
        if not filtered_results:
            st.warning("No TMDB movies match the current filters. Try relaxing them in the sidebar.")

        t_cols = st.columns(3)
        for idx, item in enumerate(filtered_results[:12]):
            with t_cols[idx % 3]:
                tmdb_id = item.get("id")
                title = item.get("title") or item.get("name") or "Unknown"
                formatted_movie = tmdb.format_tmdb_movie(item)
                formatted_movie["id"] = tmdb_id
                render_cinema_card(
                    formatted_movie,
                    key_prefix=f"tmdb_{tmdb_id}_{idx}",
                    show_match_button=False,
                )

                already_in = title.lower() in [t.lower() for t in df["title"].tolist()]
                if already_in:
                    st.info("✅ In Local Catalog")
                else:
                    if st.button(f"📥 Import to CineMatch", key=f"import_tmdb_{tmdb_id}", use_container_width=True):
                        try:
                            with st.spinner(f"Pulling full details for '{title}'..."):
                                detailed = tmdb.get_movie_details(tmdb_id)
                                formatted = tmdb.format_tmdb_movie(detailed or item)
                                added = add_movie_to_dataset(formatted)
                            if added:
                                st.toast(f"Imported '{title}'! Recommender retrained.")
                                st.rerun()
                        except requests.RequestException as error:
                            show_tmdb_error(f"Could not import '{title}'", error)


# =============================================================
# TAB 6: WATCHLIST & TASTE PROFILING
# =============================================================
with tab_watchlist:
    st.subheader(f"⭐ My Cinema Watchlist ({len(st.session_state['watchlist'])} Films)")
    st.write("Your personal collection of saved films. Generate personalized recommendations based on your collective taste profile.")

    watchlist = st.session_state["watchlist"]

    if not watchlist:
        st.info("Your watchlist is empty! Click **⭐ Watchlist** on any movie card in the app to save it here.")
    else:
        w_bar1, w_bar2, w_bar3 = st.columns([2, 1, 1])
        with w_bar1:
            saved_titles = [m["title"] for m in watchlist if "title" in m]
            if st.button("🧬 Synthesize Taste Profile Recommendations", type="primary", use_container_width=True):
                with st.spinner("Analyzing your collective taste profile..."):
                    profile_recs = recommender.recommend_for_watchlist(
                        saved_titles,
                        top_n=6,
                        genre_filter=genre_filters or None,
                        min_rating=min_rating_filter,
                        year_range=year_range_filter,
                        min_runtime=runtime_range_filter[0],
                        max_runtime=runtime_range_filter[1],
                        min_votes=min_votes_filter,
                    )
                    if profile_recs:
                        st.markdown("### 🧬 Recommended Specifically for Your Taste Profile:")
                        p_cols = st.columns(3)
                        for idx, movie in enumerate(profile_recs):
                            with p_cols[idx % 3]:
                                render_cinema_card(movie, key_prefix=f"profile_{idx}")
        with w_bar2:
            watch_df = pd.DataFrame(watchlist)
            csv_data = watch_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export CSV", csv_data, "my_watchlist.csv", "text/csv", use_container_width=True)
        with w_bar3:
            if st.button("🗑️ Clear Watchlist", use_container_width=True):
                st.session_state["watchlist"] = []
                st.rerun()

        st.markdown("---")
        st.markdown("### 📋 Saved Films:")
        w_cols = st.columns(3)
        for idx, movie in enumerate(watchlist):
            with w_cols[idx % 3]:
                render_cinema_card(movie, key_prefix=f"watch_view_{idx}", show_match_button=True)


# =============================================================
# TAB 7: CINEMA ANALYTICS & VISUALIZATIONS
# =============================================================
with tab_analytics:
    st.subheader("📊 Cinema Insights & Dataset Visualizations")
    st.write("Explore distribution patterns across cinema history, directors, genres, and ratings.")

    an_col1, an_col2 = st.columns(2)

    with an_col1:
        st.markdown("#### 📈 Distribution of IMDb Ratings")
        fig_rating = px.histogram(
            df,
            x="rating",
            nbins=15,
            color_discrete_sequence=["#b9613f"],
            title="IMDb Ratings Distribution"
        )
        fig_rating.update_layout(
            template="plotly_dark",
            paper_bgcolor="#191511",
            plot_bgcolor="#191511",
            xaxis_title="Rating (out of 10)",
            yaxis_title="Count of Movies"
        )
        st.plotly_chart(fig_rating, use_container_width=True)

    with an_col2:
        st.markdown("#### ⏱️ Runtime vs. Rating Correlation")
        fig_scatter = px.scatter(
            df,
            x="runtime",
            y="rating",
            hover_name="title",
            color="rating",
            color_continuous_scale=["#4b3022", "#b9613f", "#e5bf78"],
            size="votes",
            title="Movie Runtime vs. IMDb Rating"
        )
        fig_scatter.update_layout(
            template="plotly_dark",
            paper_bgcolor="#191511",
            plot_bgcolor="#191511",
            xaxis_title="Runtime (Minutes)",
            yaxis_title="Rating"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    an_col3, an_col4 = st.columns(2)

    with an_col3:
        st.markdown("#### 🎭 Top Genres Breakdown")
        genre_counts = {}
        for g_str in df["genres"].dropna():
            for g in str(g_str).split(","):
                g = g.strip()
                genre_counts[g] = genre_counts.get(g, 0) + 1

        genre_df = pd.DataFrame(list(genre_counts.items()), columns=["Genre", "Count"]).sort_values(by="Count", ascending=False).head(10)
        fig_donut = px.pie(
            genre_df,
            names="Genre",
            values="Count",
            hole=0.45,
            color_discrete_sequence=[
                "#b9613f",
                "#d39262",
                "#e5bf78",
                "#8b6044",
                "#694833",
                "#c8875b",
                "#a77a52",
            ],
            title="Top 10 Genres in Catalog"
        )
        fig_donut.update_layout(
            template="plotly_dark",
            paper_bgcolor="#191511",
            plot_bgcolor="#191511"
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with an_col4:
        st.markdown("#### 🎬 Top Directors in Catalog")
        dir_counts = df["director"].value_counts().head(8).reset_index()
        dir_counts.columns = ["Director", "Count"]
        fig_dir = px.bar(
            dir_counts,
            x="Director",
            y="Count",
            color="Count",
            color_continuous_scale=["#4b3022", "#b9613f", "#e5bf78"],
            title="Top Directors by Film Count"
        )
        fig_dir.update_layout(
            template="plotly_dark",
            paper_bgcolor="#191511",
            plot_bgcolor="#191511"
        )
        st.plotly_chart(fig_dir, use_container_width=True)
