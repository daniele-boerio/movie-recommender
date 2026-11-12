# WatchNext 🎬

Webapp **multi-utente** e self-hosted per tenere traccia di film e serie TV, seguire gli episodi
e ricevere consigli personalizzati. Il catalogo viene da TMDB.

In produzione su **https://movies.spassocasa.it** (Coolify sul server di casa).

**Stack:** React 18 + Vite (frontend) · FastAPI + PostgreSQL con SQLAlchemy/Alembic (backend) ·
TMDB API v3 (catalogo, in `it-IT`) · Docker Compose su Coolify

---

## Funzionalità

- **Scopri**: trending della settimana e una ricerca "intelligente", che oltre al titolo riconosce
  attori, registi, case di produzione e temi. Filtri per genere, anno, voto minimo e lingua originale.
- **Visti**: la tua libreria con voto 1–10, recensione e data di visione.
- **Diario**: i titoli visti in ordine di data.
- **Da vedere**: la watchlist.
- **Episodi**: progresso episodio per episodio di serie e anime. Segnare un episodio porta la serie
  tra i visti.
- **Per te**: consigli personalizzati con il motivo ("perché hai visto X") e filtri per tipo, generi
  esclusi, anime, voto e anni.
- **Calendario**: per i titoli in watchlist, le uscite dei film in arrivo e il prossimo episodio delle serie.
- **Liste**: liste personalizzate, anche condivise con altri utenti.
- **Community**: segui altri utenti, guarda il loro feed e il loro profilo, confronta i gusti.
- **Notifiche**: nuovi episodi delle serie che segui, inviti e aggiunte nelle liste condivise.
- **Statistiche**: generi, voti, decenni e attività mese per mese.
- **Import / export CSV**: import da Letterboxd o da un CSV generico, export completo della libreria.
- **Account**: registrazione con codice via email, reset e cambio password, cambio email, gestione
  delle sessioni attive, eliminazione dell'account.
- **PWA**: installabile su telefono, con shell offline. Tema chiaro e scuro.

### Motore di raccomandazione

Per i 30 titoli visti più di recente, il backend chiede a TMDB i titoli `recommendations` e `similar`.
Le chiamate partono in parallelo e passano dalla cache. I filtri dell'utente si applicano prima della
classifica. Ogni candidato riceve un punteggio che combina:

- quanti dei tuoi titoli lo suggeriscono;
- l'affinità con i generi che preferisci, pesata sui tuoi voti;
- il voto TMDB;
- il voto che hai dato al titolo che l'ha suggerito.

I titoli già visti o già in watchlist vengono esclusi.

---

## Architettura

```
Cloudflare / Internet
        │
Traefik (gestito da Coolify, SSL Let's Encrypt)
        │
frontend (Nginx + build React, :80)
   ├─ /        → file statici (fallback SPA su index.html)
   └─ /api/*   → proxy_pass → watchnext-backend:8000 (FastAPI, solo rete interna)
                                   ├─ PostgreSQL (risorsa Coolify separata)
                                   └─ TMDB API (client condiviso + cache LRU in memoria)
```

- Frontend e backend sono **same-origin**, perciò i token di sessione stanno in cookie `httpOnly`:
  un access token JWT breve e un refresh token con rotazione.
- Il **PostgreSQL non è nel compose**: è una risorsa Coolify a parte, raggiunta tramite le variabili
  `DB_*`. L'app ha "Connect To Predefined Network" attivo.
- Il servizio backend si chiama `watchnext-backend` e non `backend`: sulla rete condivisa `coolify`
  un nome generico collide con i servizi di altri progetti.
- **Lo schema lo gestisce Alembic**: all'avvio il container esegue `alembic upgrade head` e poi
  `uvicorn`.
- Uno **scheduler in-app** (APScheduler) controlla ogni 6 ore i nuovi episodi e crea le notifiche.
- Le API che fanno da proxy verso TMDB richiedono il login. C'è un rate limit su tutte le rotte, più
  stretto su login e registrazione, e l'IP del client viene preso anche dietro Cloudflare.

---

## Deploy su Coolify

L'app è una risorsa **Docker Compose** collegata al repo `daniele-boerio/movie-recommender`, branch
`main`. **Ogni push su `main` fa partire il deploy in automatico.**

1. Crea una risorsa **PostgreSQL** nello stesso progetto Coolify.
2. Aggiungi l'app da repository Git con build pack **Docker Compose** (`/docker-compose.yml`).
3. Attiva **Connect To Predefined Network**.
4. Assegna il dominio **solo** al servizio `frontend`. Il backend resta interno.
5. Imposta le variabili d'ambiente (vedi sotto) e fai il deploy.

### Variabili d'ambiente

| Variabile | Obbligatoria | Note |
|---|---|---|
| `TMDB_API_KEY` | sì | API key v3 di TMDB, gratuita: [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) |
| `SECRET_KEY` | sì | Firma dei JWT. Senza, il backend non parte. Usa una stringa lunga e casuale |
| `DB_HOST` | sì | In produzione è il nome interno della risorsa Postgres (il suo UUID) |
| `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | sì | Credenziali della risorsa Postgres |
| `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` | no | Senza `SMTP_SERVER`, i codici di verifica finiscono nei log del backend invece che in un'email |
| `COOKIE_SECURE` | no | Default `true`. Va messo a `false` solo in locale su http |
| `COOKIE_DOMAIN` | no | Di solito vuoto |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | no | Default 30 minuti e 90 giorni |
| `SCHEDULER_ENABLED` | no | Default `true`. Con `false` si spegne il controllo dei nuovi episodi |

### Backup

Il database ha un backup giornaliero configurato in Coolify, nella scheda Backups della risorsa
Postgres.

---

## Sviluppo in locale

Serve **Python 3.12**: con 3.13 e versioni successive `pydantic-core` non ha wheel precompilate.
Il backend legge da solo `backend/.env` (puoi partire da `.env.example`). In locale di solito si usa
il Postgres di Coolify sulla sua porta pubblica, con `COOKIE_SECURE=false`.

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: py -3.12 -m venv .venv
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (in un altro terminale)
cd frontend
npm install
npm run dev        # http://localhost:3000, inoltra /api a :8000
```

### Test

```bash
cd backend && pytest
```

I test girano su SQLite in memoria, con TMDB finto e senza scheduler né rate limit: non serve rete
né database.

### Migrazioni

Dopo aver cambiato un modello in `app/models.py`:

```bash
cd backend && alembic revision --autogenerate -m "descrizione"
```

Rileggi la migrazione generata prima di fare commit.

---

## Struttura del progetto

```
movie-recommender/
├── docker-compose.yml          # frontend + watchnext-backend (niente db)
├── .env.example
├── backend/
│   ├── Dockerfile              # alembic upgrade head && uvicorn
│   ├── alembic/versions/       # migrazioni
│   ├── requirements.txt / requirements-dev.txt
│   ├── tests/                  # pytest
│   └── app/
│       ├── main.py             # app FastAPI, middleware, router, scheduler
│       ├── config.py           # variabili d'ambiente
│       ├── database.py         # engine e sessione SQLAlchemy
│       ├── models.py / schemas.py
│       ├── auth.py             # bcrypt, JWT, cookie, utente corrente
│       ├── rate_limit.py       # slowapi + IP reale del client
│       ├── tmdb.py             # client TMDB con cache
│       ├── scheduler.py        # job periodici (nuovi episodi)
│       ├── emailer.py          # SMTP
│       ├── routers/            # auth, search, watched, watchlist, progress, stats,
│       │                       # recommendations, calendar, lists, social,
│       │                       # notifications, imports
│       └── services/           # recommender, smart_search, notifier, watch_sync
└── frontend/
    ├── Dockerfile              # build Node → Nginx
    ├── nginx.conf              # statici + proxy /api
    ├── public/                 # manifest PWA, service worker, icone
    └── src/
        ├── App.jsx             # gate di autenticazione, layout, routing, AppContext
        ├── AuthContext.jsx
        ├── api.js              # tutte le chiamate API (refresh automatico sul 401)
        ├── index.css           # design system con variabili CSS
        ├── pages/              # Discover, Watched, Diary, Watchlist, Recommendations,
        │                       # Calendar, Lists, Community, Notifications, Stats,
        │                       # Import, Settings, Person, UserProfile, Login, ...
        └── components/         # MediaCard, DetailModal, EpisodeTracker, StarRating, ...
```

Le idee per gli sviluppi futuri sono in [`.claude/roadmap.md`](.claude/roadmap.md).
