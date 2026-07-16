# WatchNext 🎬

App per tenere traccia dei film e serie TV che hai visto e ricevere consigli personalizzati basati sui tuoi gusti.

**Stack:** React + Vite (frontend) · FastAPI + SQLite (backend) · TMDB API (catalogo)

---

## Prerequisito: API Key TMDB (gratuita)

1. Vai su [https://www.themoviedb.org/signup](https://www.themoviedb.org/signup) e crea un account
2. Vai su [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
3. Richiedi una API key (tipo "Developer", gratuita e immediata)
4. Copia la **API Key (v3 auth)** — ti servirà tra poco

---

## Deploy su Coolify

### Opzione A — Da repository Git (consigliata)

1. Pusha questo progetto su un repo GitHub/GitLab/Gitea
2. In Coolify, vai nel tuo progetto → **Add New Resource** → **Private Repository (GitHub App)** o **Public Repository**
3. Seleziona il repo e il branch
4. Come build pack scegli **Docker Compose**
5. Coolify legge il `docker-compose.yml` dalla root del repo
6. Vai nella tab **Environment Variables** e aggiungi:
   ```
   TMDB_API_KEY=la_tua_api_key
   ```
7. Clicca **Deploy**

Coolify builda entrambi i servizi (frontend + backend), crea il volume per SQLite e assegna automaticamente un dominio tramite Traefik.

### Opzione B — Docker Compose diretto (senza Git)

1. In Coolify, vai nel tuo progetto → **Add New Resource** → **Docker Compose Empty**
2. Incolla il contenuto di `docker-compose.yml` nell'editor
3. **Nota:** con questo metodo devi usare immagini pre-buildate. Builda localmente e pusha su un registry:
   ```bash
   # Da locale, builda e tagga
   docker build -t tuoregistry/watchnext-backend:latest ./backend
   docker build -t tuoregistry/watchnext-frontend:latest ./frontend
   docker push tuoregistry/watchnext-backend:latest
   docker push tuoregistry/watchnext-frontend:latest
   ```
   Poi nel compose sostituisci `build:` con `image:`:
   ```yaml
   frontend:
     image: tuoregistry/watchnext-frontend:latest
   backend:
     image: tuoregistry/watchnext-backend:latest
   ```

### Dopo il deploy

- Coolify genera automaticamente un URL per il servizio `frontend` (tipo `watchnext-xxx.tuodominio.local`)
- Puoi assegnare un dominio custom dalla tab **Domains** in Coolify
- Il database SQLite è persistente nel volume `watchnext-data`

---

## Architettura Docker

```
                    ┌─────────────────────────────────┐
                    │            Traefik               │
                    │        (gestito da Coolify)       │
                    └──────────────┬──────────────────┘
                                   │ :80/:443
                    ┌──────────────▼──────────────────┐
                    │     frontend (Nginx + React)     │
                    │                                  │
                    │   /           → file statici     │
                    │   /api/*      → proxy_pass ──────┼───┐
                    └──────────────────────────────────┘   │
                                                           │
                    ┌──────────────────────────────────┐   │
                    │     backend (FastAPI/Uvicorn)     │◄──┘
                    │         :8000 (interno)           │
                    │                                  │
                    │   SQLite → /data/watchnext.db    │
                    │              ▲                    │
                    └──────────────┼───────────────────┘
                                   │
                         volume: watchnext-data
```

- **Traefik** (di Coolify) gestisce SSL e routing verso il frontend
- **Nginx** serve i file React e fa proxy di `/api/*` verso il backend
- **FastAPI** gestisce API e recommendation engine
- **SQLite** è salvato su un volume Docker persistente

---

## Dev locale (senza Docker)

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export TMDB_API_KEY="tua_key"
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Il proxy Vite inoltra automaticamente `/api/*` al backend su `:8000`.

---

## Struttura del progetto

```
movie-recommender/
├── docker-compose.yml         # Compose per Coolify
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── main.py                # FastAPI + recommendation engine
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile             # Multi-stage: Node build → Nginx
│   ├── nginx.conf             # Proxy /api → backend
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── index.css
│       ├── pages/
│       │   ├── DiscoverPage.jsx
│       │   ├── WatchedPage.jsx
│       │   └── RecommendationsPage.jsx
│       └── components/
│           ├── MediaCard.jsx
│           ├── DetailModal.jsx
│           ├── StarRating.jsx
│           └── Toast.jsx
└── README.md
```

---

## Funzionalità

- **Scopri** — titoli trending della settimana da TMDB
- **Cerca** — ricerca nel catalogo TMDB (film + serie TV)
- **I miei visti** — lista personale con filtri, ordinamento e voto 1-10
- **Per te** — consigli personalizzati con motivazione ("perché hai visto X")

### Motore di raccomandazione

Per ogni titolo visto, il backend chiede a TMDB i film/serie simili e li ordina con uno score basato su frequenza (quanti dei tuoi titoli lo suggeriscono), generi preferiti, voto TMDB e voto personale.

---

## Prossimi passi possibili

- Autenticazione utente (multi-utente)
- Watchlist "da vedere" separata
- Filtri avanzati per genere/anno
- Import da Letterboxd / Trakt
- Passaggio da SQLite a PostgreSQL per multi-utente
