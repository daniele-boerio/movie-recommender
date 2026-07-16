"""
WatchNext — Backend API
Proxy TMDB + gestione della lista "Visti".

Lo schema del database è gestito da Alembic (`alembic upgrade head`), non
dall'applicazione: all'avvio non si crea nessuna tabella.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import recommendations, search, watched

app = FastAPI(title="WatchNext API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(watched.router)
app.include_router(recommendations.router)
