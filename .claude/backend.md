# Backend — FastAPI + TMDB + SQLite

## Code structure (all in main.py)

The backend is a single-file FastAPI app. Sections in order:

1. **Config** — `TMDB_API_KEY`, `TMDB_BASE`, `DB_PATH` from env vars
2. **Database helpers** — `get_db()` returns sqlite3 connection with Row factory, `init_db()` creates the `watched` table
3. **App lifecycle** — `lifespan()` runs `init_db()` on startup
4. **TMDB helper** — `tmdb_get(path, params)` wraps all TMDB API calls with `api_key` and `language=it-IT`
5. **Pydantic models** — `WatchedItem`, `RatingUpdate`
6. **Routes** — grouped by purpose (see below)

## Database schema

```sql
watched (
    id              INTEGER PRIMARY KEY,
    tmdb_id         INTEGER NOT NULL,
    media_type      TEXT NOT NULL CHECK('movie','tv'),
    title           TEXT NOT NULL,
    poster_path     TEXT,
    vote_average    REAL,
    overview        TEXT,
    genre_ids       TEXT,          -- JSON string: "[28,12,53]"
    release_date    TEXT,
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rating          INTEGER,       -- user's personal rating 1-10
    UNIQUE(tmdb_id, media_type)
)
```

`genre_ids` is stored as a JSON string, parsed with `json.loads()` in the recommendation engine.

## Route groups

### Search & discovery (`/api/search`, `/api/trending`, `/api/details`, `/api/genres`, `/api/discover`)
Pure TMDB proxies. Always add `media_type` to results so the frontend knows if it's a movie or TV show. Multi-search can return "person" results — filter those out.

### Watched list CRUD (`/api/watched`)
- `GET` returns all rows ordered by `added_at DESC`
- `POST` inserts with UNIQUE constraint on `(tmdb_id, media_type)` — catch `IntegrityError` → 409
- `PATCH /{tmdb_id}/{media_type}` updates the personal `rating`
- `DELETE /{tmdb_id}/{media_type}` removes

### Recommendations (`/api/recommendations`)
The engine:
1. Load all watched items from DB
2. Build a genre profile: `Counter` of genre IDs weighted by personal rating
3. For each watched item (capped at 30), fetch `/recommendations` and `/similar` from TMDB
4. Score each candidate: `frequency * 10 + tmdb_vote * 2 + personal_rating * 1.5 + genre_overlap`
5. Exclude already-watched items
6. Return top N sorted by score, with `recommended_by` list (max 3 titles)

## TMDB API patterns

- Base: `https://api.themoviedb.org/3`
- Auth: query param `api_key=...`
- Movie search: `/search/movie?query=...`
- TV search: `/search/tv?query=...`
- Multi search: `/search/multi?query=...` (returns movies, TV, persons)
- Trending: `/trending/{media_type}/{time_window}`
- Details: `/{media_type}/{id}?append_to_response=credits,similar,recommendations,videos`
- Similar: `/{media_type}/{id}/similar`
- Recommendations: `/{media_type}/{id}/recommendations`
- Genres list: `/genre/{media_type}/list`
- Discover: `/discover/{media_type}?with_genres=28&sort_by=popularity.desc`
- Images: `https://image.tmdb.org/t/p/{size}{path}` — sizes: `w92`, `w154`, `w185`, `w342`, `w500`, `w780`, `original`

## Adding a new endpoint

1. Define the route with `@app.get("/api/your-endpoint")` or appropriate method
2. Use `tmdb_get()` for any TMDB calls
3. Use `get_db()` for any database operations — always close the connection
4. Add the corresponding fetch function in `frontend/src/api.js`
5. Return JSON-serializable dicts/lists

## Error handling

- TMDB errors: `httpx` raises on non-2xx, caught in the recommendation loop with `try/except` to skip failures
- DB errors: `IntegrityError` for duplicates → 409
- Missing API key: `tmdb_get()` raises 503

## If splitting into multiple files

Suggested structure:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, lifespan, CORS
│   ├── config.py        # env vars, constants
│   ├── database.py      # get_db, init_db, schema
│   ├── tmdb.py          # tmdb_get, image URL helpers
│   ├── models.py        # Pydantic schemas
│   ├── routes/
│   │   ├── search.py
│   │   ├── watched.py
│   │   └── recommendations.py
│   └── services/
│       └── recommender.py  # scoring algorithm
```
