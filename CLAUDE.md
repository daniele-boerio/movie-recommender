# WatchNext — Movie & TV Recommender

## What this project is

A self-hosted **multi-user** webapp to track watched movies/TV shows and get personalised recommendations. Uses TMDB as catalogue source, PostgreSQL for persistence, deployed on Coolify via Docker Compose.

## Stack

- **Backend:** Python 3.12 · FastAPI · PostgreSQL (SQLAlchemy + Alembic) · httpx (TMDB proxy)
- **Frontend:** React 18 · Vite · React Router 6 · Lucide icons
- **Auth:** bcrypt · JWT (python-jose) · refresh token con rotazione · cookie httpOnly
- **Infra:** Docker Compose · Nginx (reverse proxy) · Coolify on local server (192.168.1.26)
- **External API:** TMDB v3 (api.themoviedb.org/3), language `it-IT`

## Architecture

```
Traefik (Coolify) → Nginx (frontend container, :80)
                        ├─ /          → static React build
                        └─ /api/*     → proxy_pass → backend:8000 (FastAPI)
                                                        └─ PostgreSQL (risorsa Coolify separata)
```

Frontend never talks to TMDB directly — all API calls go through the backend.

Il PostgreSQL **non** è nel docker-compose: è una risorsa Coolify a sé, e il backend ci arriva
tramite le `DB_*` impostate nelle Environment Variables di Coolify.

Frontend e backend sono **same-origin** (Nginx in prod, il proxy di Vite in dev): è ciò che
permette di tenere i token in cookie `httpOnly`, irraggiungibili da JavaScript.

## Project layout

```
├── docker-compose.yml          # Coolify-compatible compose (frontend + backend, NO db)
├── backend/
│   ├── Dockerfile              # CMD: alembic upgrade head && uvicorn app.main:app
│   ├── alembic.ini
│   ├── alembic/versions/       # migrazioni (l'URL viene da app.config, non da alembic.ini)
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app, CORS, include_router
│       ├── config.py           # env vars + load_dotenv()
│       ├── database.py         # engine, SessionLocal, get_db
│       ├── models.py           # SQLAlchemy: User, EmailVerification, RefreshToken, Watched, EpisodeProgress
│       ├── schemas.py          # Pydantic
│       ├── auth.py             # hashing, JWT, cookie, get_current_user_id
│       ├── emailer.py          # SMTP (mock in dev se non configurato)
│       ├── rate_limit.py       # slowapi
│       ├── tmdb.py             # tmdb_get
│       ├── routers/            # auth, search, watched, watchlist, progress, recommendations
│       └── services/recommender.py
├── frontend/
│   ├── Dockerfile              # Multi-stage: node build → nginx serve
│   ├── nginx.conf              # Proxies /api → backend:8000
│   ├── vite.config.js          # Dev proxy on :3000 → :8000
│   ├── package.json
│   └── src/
│       ├── main.jsx            # Entry point (BrowserRouter → AuthProvider → App)
│       ├── App.jsx             # Gate auth + layout, routing, global state (AppContext)
│       ├── AuthContext.jsx     # useAuth(): user, login, register, logout, loading
│       ├── api.js              # All fetch calls + refresh automatico sul 401
│       ├── index.css           # Global styles, CSS variables, full design system
│       ├── pages/
│       │   ├── DiscoverPage.jsx      # Trending + search
│       │   ├── WatchedPage.jsx       # User's watched list with filters
│       │   ├── WatchlistPage.jsx     # Lista "Da vedere" (stessa tabella watched, status='watchlist')
│       │   ├── RecommendationsPage.jsx
│       │   ├── LoginPage.jsx
│       │   └── RegisterPage.jsx      # Due passi: email → codice + credenziali
│       └── components/
│           ├── MediaCard.jsx         # Poster card (used everywhere) + azioni rapide visto/watchlist
│           ├── DetailModal.jsx       # Full detail overlay
│           ├── EpisodeTracker.jsx    # Progresso episodi per serie/anime (dentro DetailModal)
│           ├── StarRating.jsx        # 1-10 personal rating
│           └── Toast.jsx             # Notification system
```

## Key conventions

- Backend split in moduli sotto `app/`. Ogni router in `routers/`, la logica pesante in `services/`.
- **Lo schema lo gestisce Alembic**, non l'app: nessun `create_all` all'avvio. Cambiato un modello,
  serve `alembic revision --autogenerate -m "..."` e va **riletta** la migrazione generata.
- **Ogni query su `watched` va filtrata per `user_id`.** Un endpoint che dimentica il filtro espone
  o modifica i dati altrui.
- Frontend state is managed via React Context (`useApp()` hook from App.jsx), no Redux.
- All API calls go through `frontend/src/api.js` — never fetch directly from components.
- CSS is in one file (`index.css`) using CSS custom properties. No CSS modules, no Tailwind.
- UI text is in **Italian** throughout the app.
- TMDB responses are requested with `language=it-IT`.

## Running locally (dev)

Serve Python **3.12**: su 3.13+ `pydantic-core` non ha wheel e prova a compilare da sorgente Rust.
Il `.env` (in `backend/.env`) lo carica `config.py` da solo — niente `--env-file`.

```bash
# Backend
cd backend && py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m alembic upgrade head        # allinea lo schema
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install
npm run dev                       # → http://localhost:3000 (proxies /api to :8000)
```

Lo sviluppo gira contro il **PostgreSQL di Coolify** (non uno locale): le `DB_*` nel `.env`
puntano a `192.168.1.26` sulla porta pubblica esposta da Coolify.

Senza `SMTP_SERVER` configurato, il codice di verifica finisce **nei log del backend** invece che
in un'email: è così che si testa la registrazione in locale.

## Deploy (Coolify)

Push to `daniele-boerio/movie-recommender:main` → Coolify auto-deploys via Docker Compose build pack. Set `TMDB_API_KEY` in Coolify Environment Variables. Only the frontend service needs a domain (`movies.spassocasa.it`); backend has no public domain.

## Common tasks

- **Add a new API endpoint:** add route in `backend/main.py`, add fetch function in `frontend/src/api.js`, call from component.
- **Add a new page:** create in `frontend/src/pages/`, add Route in `App.jsx`, add NavLink in sidebar.
- **Add a new component:** create in `frontend/src/components/`, use `useApp()` for global state access.
- **Change styles:** edit CSS variables at `:root` in `index.css` for theme changes, or add classes below.
- **Change recommendation logic:** edit the `get_recommendations()` function in `backend/main.py`.
