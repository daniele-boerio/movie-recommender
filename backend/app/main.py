"""
WatchNext — Backend API
Proxy TMDB + gestione della lista "Visti" + autenticazione.

Lo schema del database è gestito da Alembic (`alembic upgrade head`), non
dall'applicazione: all'avvio non si crea nessuna tabella.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .rate_limit import limiter
from .routers import auth, recommendations, search, watched

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="WatchNext API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Frontend e backend sono same-origin (nginx in prod, il proxy di Vite in dev), quindi
# i cookie di sessione non dipendono da questo. Niente allow_credentials: una pagina di
# terzi non deve poter chiamare l'API con i cookie dell'utente.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(search.router)
app.include_router(watched.router)
app.include_router(recommendations.router)
