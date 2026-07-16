# WatchNext — Movie & TV Recommender

## What this project is

A self-hosted webapp to track watched movies/TV shows and get personalised recommendations. Uses TMDB as catalogue source, SQLite for persistence, deployed on Coolify via Docker Compose.

## Stack

- **Backend:** Python 3.12 · FastAPI · SQLite · httpx (TMDB proxy)
- **Frontend:** React 18 · Vite · React Router 6 · Lucide icons
- **Infra:** Docker Compose · Nginx (reverse proxy) · Coolify on local server (192.168.1.26)
- **External API:** TMDB v3 (api.themoviedb.org/3), language `it-IT`

## Architecture

```
Traefik (Coolify) → Nginx (frontend container, :80)
                        ├─ /          → static React build
                        └─ /api/*     → proxy_pass → backend:8000 (FastAPI)
                                                        └─ SQLite @ /data/watchnext.db (Docker volume)
```

Frontend never talks to TMDB directly — all API calls go through the backend.

## Project layout

```
├── docker-compose.yml          # Coolify-compatible compose
├── backend/
│   ├── Dockerfile
│   ├── main.py                 # ALL backend code: routes, DB, recommendation engine
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile              # Multi-stage: node build → nginx serve
│   ├── nginx.conf              # Proxies /api → backend:8000
│   ├── vite.config.js          # Dev proxy on :3000 → :8000
│   ├── package.json
│   └── src/
│       ├── main.jsx            # Entry point
│       ├── App.jsx             # Layout, routing, global state (AppContext)
│       ├── api.js              # All fetch calls + image URL helpers
│       ├── index.css           # Global styles, CSS variables, full design system
│       ├── pages/
│       │   ├── DiscoverPage.jsx      # Trending + search
│       │   ├── WatchedPage.jsx       # User's watched list with filters
│       │   └── RecommendationsPage.jsx
│       └── components/
│           ├── MediaCard.jsx         # Poster card (used everywhere)
│           ├── DetailModal.jsx       # Full detail overlay
│           ├── StarRating.jsx        # 1-10 personal rating
│           └── Toast.jsx             # Notification system
```

## Key conventions

- Backend is a **single file** (`main.py`). If it grows, split into `routes/`, `services/`, `models/`.
- Frontend state is managed via React Context (`useApp()` hook from App.jsx), no Redux.
- All API calls go through `frontend/src/api.js` — never fetch directly from components.
- CSS is in one file (`index.css`) using CSS custom properties. No CSS modules, no Tailwind.
- UI text is in **Italian** throughout the app.
- TMDB responses are requested with `language=it-IT`.

## Running locally (dev)

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export TMDB_API_KEY="..."
python main.py                    # → http://localhost:8000

# Frontend (separate terminal)
cd frontend && npm install
npm run dev                       # → http://localhost:3000 (proxies /api to :8000)
```

## Deploy (Coolify)

Push to `daniele-boerio/movie-recommender:main` → Coolify auto-deploys via Docker Compose build pack. Set `TMDB_API_KEY` in Coolify Environment Variables. Only the frontend service needs a domain (`movies.spassocasa.it`); backend has no public domain.

## Common tasks

- **Add a new API endpoint:** add route in `backend/main.py`, add fetch function in `frontend/src/api.js`, call from component.
- **Add a new page:** create in `frontend/src/pages/`, add Route in `App.jsx`, add NavLink in sidebar.
- **Add a new component:** create in `frontend/src/components/`, use `useApp()` for global state access.
- **Change styles:** edit CSS variables at `:root` in `index.css` for theme changes, or add classes below.
- **Change recommendation logic:** edit the `get_recommendations()` function in `backend/main.py`.
