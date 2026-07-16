"""Configurazione centralizzata: tutte le env var si leggono da qui."""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Carica backend/.env quando si gira in locale. In Docker il file non esiste e le
# variabili arrivano dall'ambiente: load_dotenv non fa nulla e non solleva.
load_dotenv()

# --- TMDB ---
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"

# --- Database ---
DB_USER = os.getenv("DB_USER", "watchnext")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "watchnext")

# quote_plus sulla password: se contiene @ / : # (Coolify le genera casuali) senza
# escaping romperebbe il parsing dell'URL.
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
