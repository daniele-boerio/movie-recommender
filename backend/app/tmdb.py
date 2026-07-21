"""Client TMDB: tutte le chiamate all'API esterna passano da qui.

Con una cache in-memory a TTL: TMDB cambia lentamente (dettagli, provider, trending,
raccomandazioni) e molte richieste sono identiche tra utenti, quindi ricalcolarle a ogni
apertura è spreco. La cache è per-processo (basta col nostro singolo worker); niente
Redis per ora.
"""

import time
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from .config import TMDB_API_KEY, TMDB_BASE

_CACHE_TTL = 3600  # secondi (1h): buon compromesso per dati che cambiano di rado
_CACHE_MAX = 500   # tetto di sicurezza alla memoria
_cache: dict[str, tuple[float, dict]] = {}


def _cache_key(path: str, params: dict | None) -> str:
    # api_key e language non sono nei params passati qui: la chiave resta stabile.
    items = sorted((k, str(v)) for k, v in (params or {}).items())
    return path + "?" + urlencode(items)


def _prune(now: float) -> None:
    if len(_cache) < _CACHE_MAX:
        return
    for k in [k for k, (exp, _) in _cache.items() if exp <= now]:
        _cache.pop(k, None)
    if len(_cache) >= _CACHE_MAX:
        _cache.clear()  # ancora pieno di roba viva: reset semplice, si ripopola


async def tmdb_get(path: str, params: dict | None = None, *, ttl: int = _CACHE_TTL):
    if not TMDB_API_KEY:
        raise HTTPException(503, "TMDB_API_KEY non configurata. Imposta la variabile d'ambiente.")

    now = time.time()
    key = _cache_key(path, params)
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    p = {"api_key": TMDB_API_KEY, "language": "it-IT", **(params or {})}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TMDB_BASE}{path}", params=p, timeout=10)
        r.raise_for_status()
        data = r.json()

    _prune(now)
    _cache[key] = (now + ttl, data)
    return data
