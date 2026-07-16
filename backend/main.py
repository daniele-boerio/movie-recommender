"""
WatchNext — Backend API
FastAPI server that proxies TMDB requests and manages the watched list.
"""

import os
import sqlite3
from collections import Counter
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
DB_PATH = os.path.join(os.path.dirname(__file__), "watchnext.db")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched (
            id INTEGER PRIMARY KEY,
            tmdb_id INTEGER NOT NULL,
            media_type TEXT NOT NULL CHECK(media_type IN ('movie','tv')),
            title TEXT NOT NULL,
            poster_path TEXT,
            vote_average REAL,
            overview TEXT,
            genre_ids TEXT,
            release_date TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rating INTEGER,
            UNIQUE(tmdb_id, media_type)
        )
    """)
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="WatchNext API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# TMDB helper
# ---------------------------------------------------------------------------

async def tmdb_get(path: str, params: dict | None = None):
    if not TMDB_API_KEY:
        raise HTTPException(503, "TMDB_API_KEY non configurata. Imposta la variabile d'ambiente.")
    p = {"api_key": TMDB_API_KEY, "language": "it-IT", **(params or {})}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TMDB_BASE}{path}", params=p, timeout=10)
        r.raise_for_status()
        return r.json()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class WatchedItem(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" | "tv"
    title: str
    poster_path: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: str | None = None  # JSON string "[28,12,...]"
    release_date: str | None = None
    rating: int | None = None  # personal rating 1-10


class RatingUpdate(BaseModel):
    rating: int  # 1-10

# ---------------------------------------------------------------------------
# Routes — Search & Discovery
# ---------------------------------------------------------------------------

@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    media_type: str = Query("multi", regex="^(movie|tv|multi)$"),
    page: int = Query(1, ge=1),
):
    """Search TMDB for movies / TV shows."""
    if media_type == "multi":
        data = await tmdb_get("/search/multi", {"query": q, "page": page})
        # Filter to only movie/tv results
        data["results"] = [
            r for r in data.get("results", [])
            if r.get("media_type") in ("movie", "tv")
        ]
    else:
        data = await tmdb_get(f"/search/{media_type}", {"query": q, "page": page})
        for r in data.get("results", []):
            r["media_type"] = media_type
    return data


@app.get("/api/trending")
async def trending(
    media_type: str = Query("all", regex="^(movie|tv|all)$"),
    time_window: str = Query("week", regex="^(day|week)$"),
    page: int = Query(1, ge=1),
):
    """Get trending movies / TV shows."""
    data = await tmdb_get(f"/trending/{media_type}/{time_window}", {"page": page})
    data["results"] = [
        r for r in data.get("results", [])
        if r.get("media_type") in ("movie", "tv")
    ]
    return data


@app.get("/api/details/{media_type}/{tmdb_id}")
async def details(media_type: str, tmdb_id: int):
    """Full details for a movie/show, including credits and similar."""
    data = await tmdb_get(
        f"/{media_type}/{tmdb_id}",
        {"append_to_response": "credits,similar,recommendations,videos"},
    )
    data["media_type"] = media_type
    return data


@app.get("/api/genres/{media_type}")
async def genres(media_type: str):
    """Get genre list (useful for filters)."""
    return await tmdb_get(f"/genre/{media_type}/list")


@app.get("/api/discover/{media_type}")
async def discover(
    media_type: str,
    with_genres: str | None = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
):
    """Discover movies/shows by genre, sorting, etc."""
    params = {"sort_by": sort_by, "page": page}
    if with_genres:
        params["with_genres"] = with_genres
    data = await tmdb_get(f"/discover/{media_type}", params)
    for r in data.get("results", []):
        r["media_type"] = media_type
    return data

# ---------------------------------------------------------------------------
# Routes — Watched list
# ---------------------------------------------------------------------------

@app.get("/api/watched")
async def get_watched():
    """Return all watched items."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM watched ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/watched", status_code=201)
async def add_watched(item: WatchedItem):
    """Add an item to the watched list."""
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO watched
               (tmdb_id, media_type, title, poster_path, vote_average,
                overview, genre_ids, release_date, rating)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                item.tmdb_id, item.media_type, item.title,
                item.poster_path, item.vote_average, item.overview,
                item.genre_ids, item.release_date, item.rating,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(409, "Già nella lista")
    conn.close()
    return {"ok": True}


@app.patch("/api/watched/{tmdb_id}/{media_type}")
async def update_rating(tmdb_id: int, media_type: str, body: RatingUpdate):
    """Update personal rating for a watched item."""
    conn = get_db()
    cur = conn.execute(
        "UPDATE watched SET rating=? WHERE tmdb_id=? AND media_type=?",
        (body.rating, tmdb_id, media_type),
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Non trovato")
    conn.close()
    return {"ok": True}


@app.delete("/api/watched/{tmdb_id}/{media_type}")
async def remove_watched(tmdb_id: int, media_type: str):
    """Remove an item from the watched list."""
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM watched WHERE tmdb_id=? AND media_type=?",
        (tmdb_id, media_type),
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Non trovato nella lista")
    conn.close()
    return {"ok": True}

# ---------------------------------------------------------------------------
# Routes — Recommendations engine
# ---------------------------------------------------------------------------

@app.get("/api/recommendations")
async def get_recommendations(
    limit: int = Query(20, ge=1, le=50),
):
    """
    Build personalised recommendations.

    Algorithm:
    1. For each watched item, fetch TMDB "recommendations" and "similar"
    2. Score each candidate by:
       - number of watched items that recommend it (frequency)
       - genre overlap with the user's top genres
       - TMDB vote average
       - personal rating of the watched item that generated the rec
    3. Exclude already-watched items
    4. Return top N scored results
    """
    conn = get_db()
    watched_rows = conn.execute("SELECT * FROM watched").fetchall()
    conn.close()

    if not watched_rows:
        return {"results": [], "message": "Aggiungi film/serie alla tua lista per ricevere consigli!"}

    watched_set = {(r["tmdb_id"], r["media_type"]) for r in watched_rows}

    # Compute user's genre profile
    import json
    genre_counter: Counter = Counter()
    for r in watched_rows:
        if r["genre_ids"]:
            try:
                for g in json.loads(r["genre_ids"]):
                    weight = r["rating"] if r["rating"] else 5
                    genre_counter[g] += weight
            except (json.JSONDecodeError, TypeError):
                pass

    # Fetch recommendations for each watched item (cap to avoid slow requests)
    candidates: dict[tuple, dict] = {}  # (tmdb_id, media_type) -> scored item
    sample = watched_rows[:30]  # limit API calls

    for row in sample:
        mt = row["media_type"]
        tid = row["tmdb_id"]
        personal_rating = row["rating"] or 5

        for endpoint in ("recommendations", "similar"):
            try:
                data = await tmdb_get(f"/{mt}/{tid}/{endpoint}", {"page": 1})
            except Exception:
                continue

            for item in data.get("results", [])[:10]:
                item_mt = item.get("media_type", mt)
                item_id = item.get("id")
                key = (item_id, item_mt)

                if key in watched_set:
                    continue

                if key not in candidates:
                    candidates[key] = {
                        "tmdb_id": item_id,
                        "media_type": item_mt,
                        "title": item.get("title") or item.get("name", ""),
                        "poster_path": item.get("poster_path"),
                        "vote_average": item.get("vote_average", 0),
                        "overview": item.get("overview", ""),
                        "genre_ids": item.get("genre_ids", []),
                        "release_date": item.get("release_date") or item.get("first_air_date", ""),
                        "score": 0,
                        "frequency": 0,
                        "recommended_by": [],
                    }

                c = candidates[key]
                c["frequency"] += 1
                c["recommended_by"].append(row["title"])

                # Scoring
                freq_score = c["frequency"] * 10
                tmdb_score = (item.get("vote_average", 0) or 0) * 2
                personal_boost = personal_rating * 1.5
                genre_overlap = sum(
                    genre_counter.get(g, 0) for g in item.get("genre_ids", [])
                )
                c["score"] = freq_score + tmdb_score + personal_boost + genre_overlap

    # Sort by score and return top N
    ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)

    # Clean up recommended_by to max 3 unique
    for item in ranked:
        item["recommended_by"] = list(dict.fromkeys(item["recommended_by"]))[:3]

    return {"results": ranked[:limit]}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
