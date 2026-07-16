"""Client TMDB: tutte le chiamate all'API esterna passano da qui."""

import httpx
from fastapi import HTTPException

from .config import TMDB_API_KEY, TMDB_BASE


async def tmdb_get(path: str, params: dict | None = None):
    if not TMDB_API_KEY:
        raise HTTPException(503, "TMDB_API_KEY non configurata. Imposta la variabile d'ambiente.")
    p = {"api_key": TMDB_API_KEY, "language": "it-IT", **(params or {})}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TMDB_BASE}{path}", params=p, timeout=10)
        r.raise_for_status()
        return r.json()
