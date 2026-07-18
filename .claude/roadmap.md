# Roadmap — Sviluppi futuri

Priorità e dettagli implementativi per le feature in programma. Quando l'utente chiede di lavorare su una di queste, qui c'è il contesto per partire.

---

## 1. Watchlist "Da vedere" — ✅ FATTO (18/07/2026)

Implementata. Com'è andata e dove differisce da questo piano:

- **Colonna `status` su `watched`**, non una tabella separata. Il piano dava le due opzioni;
  ho scelto la colonna perché il vincolo `UNIQUE(user_id, tmdb_id, media_type)` già presente
  garantisce gratis che un titolo stia in **una sola** lista, e lo spostamento
  "da vedere" → "visto" diventa un semplice `UPDATE status` (stessa riga, stesso `id`).
  Su Postgres l'`ADD COLUMN ... server_default 'watched'` + `CHECK` è sicuro anche a tabella
  popolata (la vecchia paura della "migrazione rischiosa" era per SQLite). Migration
  `c3d9f1a4b2e6`, vincolo `ck_watched_status`.
- **Niente endpoint `/watchlist/.../watched` dedicato allo spostamento.** È `POST /api/watched`
  a fare da upsert: se il titolo è già in watchlist ne cambia lo `status` (e aggiorna
  `added_at`), altrimenti inserisce. Un solo modo per "diventare visto" = frontend più semplice.
  Endpoint effettivi: `GET/POST /api/watchlist`, `DELETE /api/watchlist/{tmdb_id}/{media_type}`.
- **Raccomandazioni:** i seed restano i soli `status='watched'` (la watchlist non dice nulla
  sui gusti, non l'ho ancora vista); l'esclusione invece copre **entrambe** le liste, così un
  titolo già in watchlist non ricompare tra i consigli. `build_recommendations(..., exclude=...)`.
- **Frontend:** `WatchlistPage.jsx` (gemella di `WatchedPage`, senza il voto), badge segnalibro
  in `MediaCard`, secondo bottone "Da vedere" in `DetailModal`, voce sidebar con icona `Bookmark`,
  `AppContext` esteso con `watchlistMap` / `isInWatchlist()` / `toggleWatchlist()`.

**Nota per il futuro:** `_serialize` della lista visti è riusata dal router watchlist
(`from .watched import _serialize`) — le due liste hanno la stessa forma JSON di proposito.

---

## 2. Autenticazione multi-utente — ✅ FATTO (17/07/2026)

Implementata. Com'è andata davvero, dove differisce da questo piano e perché:

- **Registrazione aperta con verifica email**, non a invito: chiunque chiede un codice alla
  propria email e si registra. Il codice prova che l'indirizzo è suo, **non** limita chi entra.
  Scelta consapevole. Il codice è legato all'email richiedente (altrimenti non verificherebbe nulla),
  hashato con bcrypt, scade in 15 min, max 5 tentativi, rate limit 3/ora per IP.
- **Token in cookie `httpOnly`**, non in `localStorage`: FE e BE sono same-origin, quindi si può,
  e un XSS non può rubare quello che JavaScript non vede. Niente header `Authorization`.
  Access token (JWT, 30 min) + refresh opaco (90 giorni) con rotazione e **reuse detection**.
- **bcrypt diretto**, non passlib (non manutenuto e in conflitto con bcrypt ≥ 4.1).
- **PostgreSQL fatto insieme** (punto 6), non dopo: il DB era vuoto, quindi costava quasi nulla.

**⚠️ L'errore che c'era in questo piano** (lasciato come monito): proponeva solo
`ALTER TABLE watched ADD COLUMN user_id`. **Non basta.** `watched` aveva `UNIQUE(tmdb_id, media_type)`:
senza portarlo a `UNIQUE(user_id, tmdb_id, media_type)` il secondo utente che segna un film già
segnato da un altro prende un 409. Su SQLite avrebbe anche richiesto di ricostruire la tabella,
perché non sa rimuovere un vincolo con `ALTER TABLE`.

Vale per qualsiasi feature futura: **aggiungere `user_id` a una tabella significa rivedere anche
i suoi vincoli univoci**, non solo aggiungere la colonna.

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

## 6. Migrazione da SQLite a PostgreSQL — ✅ FATTO (17/07/2026)

Fatta insieme all'auth (punto 2), approfittando del DB vuoto: nessun travaso di dati.

Differenze rispetto al piano sotto: il Postgres **non** sta nel docker-compose, è una risorsa
Coolify separata (le `DB_*` arrivano dalle Environment Variables). Si usa SQLAlchemy sincrono +
psycopg2 + Alembic per le migrazioni, che girano al boot del container
(`CMD: alembic upgrade head && uvicorn ...`).

Due trappole incontrate, per il futuro:
- **La porta interna è 5432, non quella pubblica.** Coolify espone il Postgres sull'host mappando
  `5433 → 5432`: parlando al container per nome si è dentro la rete Docker, dove vale la 5432.
- **Le risorse Coolify nascono su reti Docker separate.** Se il backend non condivide una rete col
  Postgres, il nome del container non si risolve (`could not translate host name`) — che è un
  fallimento **DNS**, non di connessione: distinguere i due errori fa risparmiare ore.

Il piano originale, per riferimento:

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
