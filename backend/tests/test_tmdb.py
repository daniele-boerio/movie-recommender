"""Client TMDB: connessione riusata e cache LRU (senza rete: trasporto finto)."""

import asyncio

import httpx
import pytest

from app import tmdb


@pytest.fixture
def fake_tmdb(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"path": request.url.path})

    clients = []

    def make_client():
        c = httpx.AsyncClient(base_url=tmdb.TMDB_BASE, transport=httpx.MockTransport(handler))
        clients.append(c)
        return c

    monkeypatch.setattr(tmdb, "TMDB_API_KEY", "k")
    monkeypatch.setattr(tmdb, "_cache", type(tmdb._cache)())
    def get_client():
        if not clients:
            make_client()
        return clients[0]

    monkeypatch.setattr(tmdb, "_get_client", get_client)
    return calls, clients


def test_cache_evita_la_seconda_chiamata(fake_tmdb):
    calls, _ = fake_tmdb

    async def go():
        a = await tmdb.tmdb_get("/movie/1")
        b = await tmdb.tmdb_get("/movie/1")
        return a, b

    a, b = asyncio.run(go())
    assert a == b
    assert calls == ["/3/movie/1"]  # il base_url /3 resta nel percorso


def test_lru_scarta_la_meno_usata_non_tutto(fake_tmdb, monkeypatch):
    calls, _ = fake_tmdb
    monkeypatch.setattr(tmdb, "_CACHE_MAX", 2)

    async def go():
        await tmdb.tmdb_get("/a")
        await tmdb.tmdb_get("/b")
        await tmdb.tmdb_get("/a")  # /a torna recente
        await tmdb.tmdb_get("/c")  # piena: esce /b, non tutto
        await tmdb.tmdb_get("/a")  # ancora in cache

    asyncio.run(go())
    assert calls == ["/3/a", "/3/b", "/3/c"]
    assert set(tmdb._cache) == {"/a?", "/c?"}


def test_client_condiviso_nello_stesso_loop(monkeypatch):
    monkeypatch.setattr(tmdb, "_client", None)

    async def go():
        c1 = tmdb._get_client()
        c2 = tmdb._get_client()
        await tmdb.close_client()
        return c1, c2

    c1, c2 = asyncio.run(go())
    assert c1 is c2
