"""Client TMDB: tutte le chiamate all'API esterna passano da qui.

Due cose tengono basse le attese:

- **Un solo client HTTP condiviso**, con keep-alive: prima ogni chiamata apriva una
  connessione nuova (DNS + TCP + TLS verso TMDB), e quel giro costava più della risposta.
- **Una cache LRU in-memory a TTL**: TMDB cambia lentamente (dettagli, provider, trending,
  raccomandazioni) e molte richieste sono identiche tra utenti. Piena, scarta le voci
  usate meno di recente, invece di svuotarsi tutta di colpo come prima. È per-processo
  (basta col nostro singolo worker); niente Redis per ora.
"""

import asyncio
import time
from collections import OrderedDict
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from .config import TMDB_API_KEY, TMDB_BASE

_CACHE_TTL = 3600   # secondi (1h): buon compromesso per dati che cambiano di rado
_CACHE_MAX = 3000   # tetto alla memoria: le risposte TMDB sono qualche decina di KB al massimo
_cache: "OrderedDict[str, tuple[float, dict]]" = OrderedDict()

# Il client è legato all'event loop in cui nasce: lo ricreiamo se il loop cambia (succede
# nei test, dove ogni TestClient ne gira uno suo).
_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_client() -> httpx.AsyncClient:
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client.is_closed or _client_loop is not loop:
        _client = httpx.AsyncClient(
            base_url=TMDB_BASE,
            timeout=httpx.Timeout(10, pool=30),  # in coda per il pool: fino a 30s
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        _client_loop = loop
    return _client


async def close_client() -> None:
    """Chiamata allo spegnimento dell'app."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _cache_key(path: str, params: dict | None) -> str:
    # api_key e language non sono nei params passati qui: la chiave resta stabile.
    items = sorted((k, str(v)) for k, v in (params or {}).items())
    return path + "?" + urlencode(items)


def _cache_put(key: str, expires: float, data: dict) -> None:
    _cache[key] = (expires, data)
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)  # la meno usata di recente


async def tmdb_get(path: str, params: dict | None = None, *, ttl: int = _CACHE_TTL):
    if not TMDB_API_KEY:
        raise HTTPException(503, "TMDB_API_KEY non configurata. Imposta la variabile d'ambiente.")

    now = time.time()
    key = _cache_key(path, params)
    cached = _cache.get(key)
    if cached:
        if cached[0] > now:
            _cache.move_to_end(key)
            return cached[1]
        _cache.pop(key, None)

    p = {"api_key": TMDB_API_KEY, "language": "it-IT", **(params or {})}
    r = await _get_client().get(path, params=p)
    r.raise_for_status()
    data = r.json()

    _cache_put(key, now + ttl, data)
    return data
