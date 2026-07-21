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

from .config import SCHEDULER_ENABLED
from .rate_limit import limiter
from .routers import (
    auth,
    calendar,
    imports,
    lists,
    notifications,
    progress,
    recommendations,
    search,
    social,
    stats,
    watched,
    watchlist,
)

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
app.include_router(watchlist.router)
app.include_router(progress.router)
app.include_router(stats.router)
app.include_router(imports.router)
app.include_router(calendar.router)
app.include_router(lists.router)
app.include_router(social.router)
app.include_router(notifications.router)
app.include_router(recommendations.router)


# Scheduler in-app: avviato all'apertura, fermato allo spegnimento. Disattivabile con
# SCHEDULER_ENABLED=false (test). L'import è locale per non tirarsi dentro APScheduler
# quando lo scheduler è spento.
@app.on_event("startup")
async def _start_scheduler() -> None:
    # async: garantisce che il loop uvicorn sia in esecuzione quando AsyncIOScheduler
    # va a prenderlo con get_event_loop().
    if SCHEDULER_ENABLED:
        from .scheduler import start_scheduler

        start_scheduler()


@app.on_event("shutdown")
def _stop_scheduler() -> None:
    if SCHEDULER_ENABLED:
        from .scheduler import stop_scheduler

        stop_scheduler()
