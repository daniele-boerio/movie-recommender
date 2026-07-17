# Backend — FastAPI + TMDB + PostgreSQL

## Code structure

Split in moduli sotto `backend/app/`:

1. **`config.py`** — tutte le env var, `load_dotenv()`, `DATABASE_URL` (password via `quote_plus`)
2. **`database.py`** — `engine` (con `pool_pre_ping`), `SessionLocal`, `Base`, `get_db()`
3. **`models.py`** — SQLAlchemy: `User`, `EmailVerification`, `RefreshToken`, `Watched`
4. **`schemas.py`** — Pydantic
5. **`auth.py`** — hashing, JWT, cookie, `get_current_user_id`
6. **`emailer.py`** — SMTP, con mock in dev
7. **`rate_limit.py`** — slowapi
8. **`tmdb.py`** — `tmdb_get(path, params)`, aggiunge `api_key` e `language=it-IT`
9. **`routers/`** — `auth`, `search`, `watched`, `recommendations`
10. **`services/recommender.py`** — algoritmo di scoring

`main.py` contiene solo app, CORS, handler del rate limit e `include_router`.

## Database schema

```sql
users (id, email UNIQUE, username UNIQUE, password_hash,
       token_version INT DEFAULT 1, created_at)      -- email/username SEMPRE lowercase

email_verifications (id, email, code_hash, expires_at, consumed_at,
                     attempts INT DEFAULT 0, created_at)

refresh_tokens (id, user_id FK→users ON DELETE CASCADE, token_hash UNIQUE,
                family_id, expires_at, created_at, used_at, revoked_at, user_agent)

watched (id, user_id FK→users ON DELETE CASCADE, tmdb_id, media_type CHECK('movie','tv'),
         title, poster_path, vote_average, overview, genre_ids, release_date,
         added_at, rating,
         UNIQUE(user_id, tmdb_id, media_type))       -- ← user_id DEVE esserci
```

`genre_ids` è una stringa JSON, parsata con `json.loads()` nel motore di raccomandazione.

**Il vincolo su `watched` include `user_id`**: senza, due utenti non potrebbero avere lo stesso
titolo in lista (il secondo prenderebbe un 409). Vale per ogni tabella per-utente che aggiungerai.

## Migrazioni (Alembic)

Lo schema **non** lo crea l'app: nessun `create_all`. In produzione le migrazioni girano al boot
(`CMD: alembic upgrade head && uvicorn ...`), in locale si lanciano a mano.

```bash
cd backend
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "descrizione"
.venv/Scripts/python.exe -m alembic upgrade head
```

`alembic/env.py` prende `DATABASE_URL` e i metadati da `app.config` / `app.database`: l'URL **non**
sta in `alembic.ini`, così non si duplica un segreto in un file committato.

**Rileggi sempre la migrazione autogenerata.** Alembic sbaglia o omette: crea le foreign key
con nome `None` (e allora il `downgrade` non gira — vanno nominate a mano), e non sa che una
colonna `NOT NULL` senza default fallisce su una tabella già popolata.

## Auth

**Registrazione in due passi**
1. `POST /api/auth/register/request {email}` — genera il codice, lo spedisce, `3/hour` per IP.
   Risposta **sempre identica** anche se l'email esiste già: altrimenti l'endpoint rivelerebbe
   quali indirizzi hanno un account.
2. `POST /api/auth/register {email, code, username, password}` — valida e crea l'utente.

Il codice è di 6 caratteri (alfabeto senza `0/O/1/I/L`), hashato con **bcrypt** perché a bassa
entropia, scade in 15 min, max 5 tentativi.

**Sessione** — `POST /api/auth/login` · `/refresh` · `/logout`, `GET /api/auth/me`, `/sessions`.

**Cookie**: `access_token` (JWT, 30 min, `path=/api`) e `refresh_token` (opaco, 90 giorni,
`path=/api/auth`, in DB solo l'hash SHA-256). Entrambi `httpOnly` + `SameSite=Lax`; `Secure`
governato da `COOKIE_SECURE` (**`false` in locale**, altrimenti su http il browser li scarta).

**Rotazione e reuse detection**: ogni `/refresh` ruota il token. Se ne viene presentato uno già
usato è un replay (cookie copiato): non potendo sapere chi sia la vittima, si revoca l'**intera
famiglia** e si logga un warning. È il posto dove guardare se un utente viene sloggato di colpo.

**`token_version`** su `User`: incrementandola si invalidano tutti gli access token già emessi
(es. al cambio password) senza aspettarne la scadenza.

**Anti-enumeration**: `/login` confronta con `_DUMMY_PASSWORD_HASH` quando l'utente non esiste,
così utente inesistente e password errata costano lo stesso e rispondono identico.

## Route groups

### Search & discovery (`/api/search`, `/trending`, `/details`, `/genres`, `/discover`)
Puri proxy TMDB, **pubblici** (nessun dato dell'utente). Aggiungere sempre `media_type` ai
risultati. `/search/multi` restituisce anche le persone: vanno filtrate.

### Watched (`/api/watched`) — richiede auth
`GET` la lista dell'utente · `POST` (`IntegrityError` → 409) · `PATCH /{tmdb_id}/{media_type}`
per il voto · `DELETE`. **Ogni query filtra per `user_id`.** Un titolo non proprio dà **404**,
non 403: non riveliamo cosa hanno gli altri.

### Recommendations (`/api/recommendations`) — richiede auth
1. Carica i visti dell'utente (`order_by(added_at.desc())` esplicito: Postgres non garantisce
   un ordine, e il motore campiona i primi 30)
2. Profilo dei generi: `Counter` pesato sul voto personale
3. Per ogni titolo (max 30) chiede `/recommendations` e `/similar` a TMDB
4. Score: `frequency*10 + tmdb_vote*2 + personal_rating*1.5 + genre_overlap`
5. Esclude i già visti, restituisce i primi N con `recommended_by` (max 3)

## TMDB API patterns

- Base: `https://api.themoviedb.org/3` · auth via query param `api_key=...`
- Search: `/search/movie` · `/search/tv` · `/search/multi`
- Trending: `/trending/{media_type}/{time_window}`
- Details: `/{media_type}/{id}?append_to_response=credits,similar,recommendations,videos`
- Similar / Recommendations: `/{media_type}/{id}/similar` · `/recommendations`
- Genres: `/genre/{media_type}/list` · Discover: `/discover/{media_type}?with_genres=28`
- Images: `https://image.tmdb.org/t/p/{size}{path}` — `w92`…`w780`, `original`

## Adding a new endpoint

1. Route nel router giusto sotto `routers/` (o un nuovo router + `include_router` in `main.py`)
2. `Depends(get_db)` per il DB, `Depends(get_current_user_id)` se tocca dati dell'utente
3. **Filtra per `user_id`** ogni query su dati per-utente
4. `tmdb_get()` per TMDB
5. Aggiungi la fetch in `frontend/src/api.js`

## Error handling

- TMDB: `httpx` solleva su non-2xx; nel motore di raccomandazione è dentro `try/except` per
  saltare i fallimenti senza far cadere l'intera risposta
- Duplicati: `IntegrityError` → 409 · Non trovato / non tuo → 404
- `TMDB_API_KEY` mancante → 503 · `SECRET_KEY` mancante → l'app **non parte** (fail-fast voluto)
