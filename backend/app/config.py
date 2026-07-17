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

# --- Auth ---
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# L'access token è a vita breve: sta in un cookie httpOnly, ma se comunque trapelasse
# la finestra di abuso è di minuti. La sessione lunga la regge il refresh token.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 90))

# In locale si gira su http: con Secure attivo il browser scarterebbe i cookie
# e il login non funzionerebbe mai. In produzione deve restare true.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() != "false"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None

# --- Codice di verifica email ---
CODE_EXPIRE_MINUTES = 15
CODE_MAX_ATTEMPTS = 5

# --- SMTP ---
# Se non configurato, l'email viene loggata invece che spedita (comodo in sviluppo).
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@watchnext.local")
