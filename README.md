# WatchNext 🎬

App per tenere traccia dei film e serie TV che hai visto e ricevere consigli personalizzati basati sui tuoi gusti.

**Stack:** React + Vite (frontend) · FastAPI + SQLite (backend) · TMDB API (catalogo)

---

## Setup rapido

### 1. Ottieni una API key gratuita da TMDB

1. Vai su [https://www.themoviedb.org/signup](https://www.themoviedb.org/signup) e crea un account
2. Vai su [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
3. Richiedi una API key (tipo "Developer", è gratuita e immediata)
4. Copia la **API Key (v3 auth)**

### 2. Avvia il backend

```bash
cd backend

# Crea un virtual environment (consigliato)
python -m venv venv
source venv/bin/activate   # Linux/Mac
# oppure: venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt

# Imposta la API key
export TMDB_API_KEY="la_tua_api_key_qui"   # Linux/Mac
# oppure: set TMDB_API_KEY=la_tua_api_key_qui  # Windows

# Avvia il server
python main.py
```

Il backend sarà disponibile su `http://localhost:8000`.
La documentazione API interattiva è su `http://localhost:8000/docs`.

### 3. Avvia il frontend

```bash
cd frontend

# Installa dipendenze
npm install

# Avvia il dev server
npm run dev
```

Il frontend sarà disponibile su `http://localhost:3000`.
Il proxy Vite inoltra automaticamente le chiamate `/api/*` al backend.

---

## Funzionalità

- **Scopri** — titoli trending della settimana da TMDB
- **Cerca** — ricerca libera nel catalogo TMDB (film + serie TV)
- **I miei visti** — la tua lista personale, filtrabile e ordinabile, con voto personale 1-10
- **Per te** — consigli personalizzati generati analizzando i tuoi gusti

### Come funziona il motore di raccomandazione

Per ogni titolo nella tua lista, il backend chiede a TMDB i film/serie simili e raccomandati, poi li ordina con uno score basato su:

- **Frequenza:** quanti dei tuoi titoli raccomandano lo stesso risultato
- **Generi:** sovrapposizione con i generi che guardi di più
- **Voto TMDB:** qualità media secondo gli utenti TMDB
- **Tuo voto personale:** i titoli che hai votato alto pesano di più

---

## Struttura del progetto

```
movie-recommender/
├── backend/
│   ├── main.py              # FastAPI app (API + recommendation engine)
│   ├── requirements.txt
│   └── watchnext.db          # SQLite (creato automaticamente)
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Layout + routing + state globale
│   │   ├── api.js            # Chiamate API
│   │   ├── pages/
│   │   │   ├── DiscoverPage  # Trending + ricerca
│   │   │   ├── WatchedPage   # Lista visti
│   │   │   └── RecommendationsPage
│   │   └── components/
│   │       ├── MediaCard     # Card film/serie
│   │       ├── DetailModal   # Modale dettaglio
│   │       ├── StarRating    # Voto personale
│   │       └── Toast         # Notifiche
│   ├── vite.config.js
│   └── package.json
└── README.md
```

---

## API Endpoints

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/search?q=...&media_type=...` | Cerca film/serie |
| GET | `/api/trending?media_type=...` | Trending settimanale |
| GET | `/api/details/{type}/{id}` | Dettagli completi |
| GET | `/api/genres/{type}` | Lista generi |
| GET | `/api/discover/{type}` | Scopri per genere |
| GET | `/api/watched` | Lista visti |
| POST | `/api/watched` | Aggiungi ai visti |
| PATCH | `/api/watched/{id}/{type}` | Aggiorna voto |
| DELETE | `/api/watched/{id}/{type}` | Rimuovi dai visti |
| GET | `/api/recommendations?limit=20` | Consigli personalizzati |

---

## Prossimi passi possibili

- Autenticazione utente (multi-utente)
- Watchlist "da vedere" separata dalla lista "visti"
- Filtri avanzati per genere/anno/voto nella ricerca
- Import da altre piattaforme (Letterboxd, Trakt)
- Deploy su Render/Railway (backend) + Vercel/Netlify (frontend)
