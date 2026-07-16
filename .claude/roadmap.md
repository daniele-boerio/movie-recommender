# Roadmap — Sviluppi futuri

Priorità e dettagli implementativi per le feature in programma. Quando l'utente chiede di lavorare su una di queste, qui c'è il contesto per partire.

---

## 1. Watchlist "Da vedere"

Aggiungere una lista separata per i titoli che l'utente vuole guardare in futuro, distinta dalla lista "Visti".

**Database:**
```sql
ALTER TABLE watched ADD COLUMN status TEXT NOT NULL DEFAULT 'watched'
  CHECK(status IN ('watched', 'watchlist'));
```
Oppure creare una tabella `watchlist` separata con la stessa struttura di `watched` (più semplice da gestire, nessuna migrazione rischiosa).

**Backend:**
- `GET /api/watchlist` — lista dei "da vedere"
- `POST /api/watchlist` — aggiungi alla watchlist
- `DELETE /api/watchlist/{tmdb_id}/{media_type}` — rimuovi
- `POST /api/watchlist/{tmdb_id}/{media_type}/watched` — sposta da watchlist a visti (cancella da watchlist + inserisci in watched)

**Frontend:**
- Nuova pagina `WatchlistPage.jsx` con la stessa struttura di `WatchedPage`
- Nel `DetailModal`, aggiungere un secondo bottone "Da vedere" accanto a "Ho visto questo"
- Nel `MediaCard`, badge diverso per watchlist (es. icona bookmark outline vs check)
- Nuova voce nella sidebar con icona `Bookmark` da lucide-react
- Aggiornare `AppContext` con `watchlistMap`, `isInWatchlist()`, `toggleWatchlist()`

**Logica raccomandazioni:**
- I titoli nella watchlist NON devono apparire nei consigli (già "salvati")
- Opzionale: nella pagina "Per te", evidenziare i risultati che sono già nella watchlist

---

## 2. Autenticazione multi-utente

Permettere a più persone di usare la stessa istanza, ognuno con la propria lista.

**Approccio consigliato:** JWT semplice, senza OAuth per ora.

**Database:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aggiungere foreign key a watched (e watchlist)
ALTER TABLE watched ADD COLUMN user_id INTEGER REFERENCES users(id);
```

**Backend:**
- `POST /api/auth/register` — crea utente (hash con `bcrypt` o `passlib`)
- `POST /api/auth/login` — restituisce JWT token
- Middleware/dependency FastAPI che estrae `user_id` dal token JWT
- Tutte le query `watched` filtrate per `user_id`
- Dipendenza aggiuntiva: `python-jose[cryptography]` e `passlib[bcrypt]`

**Frontend:**
- Pagina login/register
- Salvare JWT in `localStorage`, inviare come header `Authorization: Bearer ...`
- Wrapper in `api.js` che aggiunge l'header automaticamente
- Redirect a login se 401
- Mostrare username nella sidebar

**Nota:** se si aggiunge auth, valutare il passaggio a PostgreSQL (vedi punto 6).

---

## 3. Filtri avanzati nella ricerca

Aggiungere filtri per genere, anno, voto minimo nella pagina Scopri/Cerca.

**Backend:** l'endpoint `/api/discover/{media_type}` già supporta parametri TMDB:
- `with_genres` — comma-separated genre IDs
- `primary_release_date.gte` / `.lte` — range anno (film)
- `first_air_date.gte` / `.lte` — range anno (TV)
- `vote_average.gte` — voto minimo
- `sort_by` — `popularity.desc`, `vote_average.desc`, `release_date.desc`

Basta esporre questi parametri nel frontend.

**Frontend:**
- Caricare generi da `/api/genres/movie` e `/api/genres/tv` al mount
- Pannello filtri collassabile sotto la search bar in `DiscoverPage`
- Componenti: multi-select generi (chip/tag cliccabili), range slider anno, select ordinamento
- Quando un filtro è attivo, usare `/api/discover` invece di `/api/search`
- Mostrare filtri attivi come chip rimovibili sopra la griglia

---

## 4. Import da piattaforme esterne

Permettere l'import massivo da Letterboxd, Trakt, o file CSV.

### Letterboxd
Letterboxd permette di esportare un CSV dalla pagina profilo → Settings → Import & Export → Export Your Data. Il file `watched.csv` contiene: `Date`, `Name`, `Year`, `Letterboxd URI`, `Rating`.

**Backend:**
- `POST /api/import/letterboxd` — riceve il CSV come file upload
- Per ogni riga, cerca su TMDB con `/search/movie?query={Name}&year={Year}`
- Prende il primo risultato, crea la entry in `watched` con rating convertito (Letterboxd usa 0.5-5.0, convertire a 1-10)
- Restituisce report: quanti importati, quanti non trovati, quanti duplicati

### Trakt
Trakt ha una API pubblica. Serve registrare un'app su trakt.tv per ottenere un `client_id`.
- `GET https://api.trakt.tv/users/{username}/watched/movies`
- `GET https://api.trakt.tv/users/{username}/watched/shows`
- Ogni item ha un `ids.tmdb` che mappa direttamente al nostro `tmdb_id`

### CSV generico
- `POST /api/import/csv` — accetta CSV con colonne `title`, `year`, `type` (movie/tv), `rating`
- Cerca ciascuno su TMDB e inserisce

**Frontend:**
- Pagina o modale di import con drag & drop file
- Progress bar durante l'import
- Report finale con risultati

---

## 5. Statistiche personali

Dashboard con statistiche sui gusti dell'utente.

**Dati calcolabili dal database:**
- Totale film / serie viste
- Distribuzione per genere (pie chart o bar chart)
- Rating medio dato dall'utente
- Titolo con voto più alto / più basso
- Generi più guardati vs generi con voto medio più alto
- Timeline: aggiunte per mese (line chart)
- Registi / attori più visti (richiede fetch dei credits da TMDB per ogni titolo)

**Frontend:**
- Nuova pagina `StatsPage.jsx`
- Usare `recharts` (già disponibile come dipendenza possibile) per i grafici
- Layout a cards con numeri grandi + grafici sotto
- Sidebar: icona `BarChart3` da lucide-react

**Backend:**
- `GET /api/stats` — calcola e restituisce tutto server-side
- Per i dati che richiedono TMDB (registi, attori), considerare di salvare i credits in DB al momento dell'aggiunta per evitare N chiamate API

---

## 6. Migrazione da SQLite a PostgreSQL

Necessaria se si implementa il multi-utente o si vuole più robustezza.

**docker-compose.yml:**
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: watchnext
      POSTGRES_PASSWORD: ${SERVICE_PASSWORD_DB}
      POSTGRES_DB: watchnext
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U watchnext"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    # ... aggiungere:
    environment:
      - DATABASE_URL=postgresql://watchnext:${SERVICE_PASSWORD_DB}@db:5432/watchnext
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres-data:
```

**Backend:**
- Sostituire `sqlite3` con `asyncpg` o `databases` + `sqlalchemy`
- Oppure approccio più semplice: `psycopg2-binary` sincrono (stile simile a sqlite3 attuale)
- Cambiare `get_db()` per restituire una connessione PostgreSQL
- Aggiornare lo schema SQL (SERIAL invece di INTEGER PRIMARY KEY, TIMESTAMPTZ, ecc.)
- Aggiungere `psycopg2-binary` a `requirements.txt`

**Migrazione dati:**
Script Python che legge da SQLite e inserisce in PostgreSQL, da eseguire una volta.

---

## 7. Notifiche nuove uscite

Avvisare l'utente quando esce un nuovo film/serie simile ai suoi gusti o un seguito di qualcosa che ha visto.

**Backend:**
- Job schedulato (es. con `apscheduler` o cron in Docker) che gira 1x al giorno
- Per ogni titolo visto che è una serie TV, controllare `/tv/{id}` per nuove stagioni
- Per generi preferiti, controllare `/discover` con `primary_release_date.gte=oggi`
- Salvare notifiche in tabella `notifications (id, user_id, message, tmdb_id, media_type, read, created_at)`

**Frontend:**
- Icona campanella nella sidebar con badge contatore
- Dropdown o pagina con lista notifiche
- Click su notifica → apre DetailModal del titolo

---

## 8. Miglioramenti al motore di raccomandazione

### Keyword-based scoring
TMDB ha un endpoint `/movie/{id}/keywords` e `/tv/{id}/keywords`. Le keyword (es. "time travel", "heist", "dystopia") sono più granulari dei generi per trovare affinità. Aggiungere keyword overlap allo score.

### Collaborative filtering leggero
Se multi-utente: "utenti che hanno visto X e Y hanno anche visto Z". Richiede PostgreSQL e una query di co-occorrenza sulle liste di tutti gli utenti.

### Peso temporale
Titoli aggiunti di recente dovrebbero pesare di più nelle raccomandazioni rispetto a quelli aggiunti mesi fa. Aggiungere un moltiplicatore decay basato su `added_at`.

### Esclusione generi
Permettere all'utente di escludere generi dai consigli (es. "non mi consigliare horror"). Salvare in una tabella `user_preferences` o in un campo JSON nel profilo utente.

### Cache raccomandazioni
Il calcolo attuale fa N × 2 chiamate TMDB (N = titoli visti, × 2 per similar + recommendations). Cacheare i risultati in una tabella `recommendation_cache (tmdb_id, media_type, recommendations_json, fetched_at)` e rigenerare solo se `fetched_at` > 7 giorni.

---

## 9. PWA e mobile

Rendere l'app installabile come PWA per usarla come app mobile.

- Aggiungere `manifest.json` in `frontend/public/`
- Aggiungere service worker per caching offline (almeno la lista visti)
- Icona app (generare da un poster stilizzato o dal logo WatchNext)
- Il CSS è già responsive, ma testare e ottimizzare touch targets e swipe gestures

---

## 10. Condivisione e social

- **Lista pubblica:** URL condivisibile della propria lista visti (sola lettura)
- **Confronto:** "io e te abbiamo visto X in comune, tu hai visto Y che io non ho visto"
- **Consiglia a un amico:** bottone per condividere un titolo via link/WhatsApp

Richiede multi-utente (punto 2) come prerequisito.

---

## Ordine suggerito di implementazione

1. **Watchlist "Da vedere"** — piccola, utile subito, nessuna dipendenza
2. **Filtri avanzati** — usa endpoint già esistente, solo lavoro frontend
3. **Statistiche** — gratificante, solo lettura, nessun rischio
4. **Import Letterboxd/CSV** — popola la lista velocemente, migliora i consigli
5. **Miglioramenti recommender** — cache + keyword scoring
6. **Autenticazione** — prerequisito per le feature social
7. **PostgreSQL** — da fare insieme o subito dopo l'auth
8. **Notifiche** — richiede job schedulato, più complesso
9. **PWA** — nice to have, indipendente dal resto
10. **Social** — richiede auth + PostgreSQL
