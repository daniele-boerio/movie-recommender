# Commands

## Dev

```bash
# Start backend (from project root)
cd backend && source venv/bin/activate && TMDB_API_KEY="..." python main.py

# Start frontend (from project root)
cd frontend && npm run dev

# Run both (with two terminals or use & for background)
```

## Lint / format

```bash
# Python
pip install ruff
ruff check backend/
ruff format backend/

# JavaScript
cd frontend && npx eslint src/
```

## Test backend endpoints

```bash
# Search
curl "http://localhost:8000/api/search?q=inception&media_type=movie"

# Trending
curl "http://localhost:8000/api/trending?media_type=all"

# Add to watched
curl -X POST http://localhost:8000/api/watched \
  -H "Content-Type: application/json" \
  -d '{"tmdb_id": 27205, "media_type": "movie", "title": "Inception"}'

# Get watched list
curl http://localhost:8000/api/watched

# Get recommendations
curl "http://localhost:8000/api/recommendations?limit=10"

# Remove from watched
curl -X DELETE http://localhost:8000/api/watched/27205/movie
```

## Docker

```bash
# Build locally
docker compose build

# Run locally
TMDB_API_KEY="..." docker compose up

# Build single service
docker compose build frontend
docker compose build backend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Shell into running container
docker compose exec backend bash
docker compose exec frontend sh
```

## Database

```bash
# Open SQLite from backend container
docker compose exec backend python -c "
import sqlite3, json
conn = sqlite3.connect('/data/watchnext.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM watched').fetchall()
for r in rows:
    print(dict(r))
conn.close()
"

# Count items
docker compose exec backend python -c "
import sqlite3
conn = sqlite3.connect('/data/watchnext.db')
print('Total:', conn.execute('SELECT COUNT(*) FROM watched').fetchone()[0])
print('Movies:', conn.execute(\"SELECT COUNT(*) FROM watched WHERE media_type='movie'\").fetchone()[0])
print('TV:', conn.execute(\"SELECT COUNT(*) FROM watched WHERE media_type='tv'\").fetchone()[0])
conn.close()
"
```
