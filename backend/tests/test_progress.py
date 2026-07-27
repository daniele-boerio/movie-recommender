"""Progresso episodi: una puntata vista porta la serie tra i "Visti".

TMDB è finto (`watch_sync.tmdb_get`): serve solo a dare titolo e metadati alla riga
creata automaticamente.
"""

import json

import pytest

from app.services import watch_sync

from .helpers import register

BREAKING_BAD = {
    "id": 1396,
    "name": "Breaking Bad",
    "poster_path": "/bb.jpg",
    "vote_average": 8.9,
    "overview": "Un professore di chimica…",
    "genres": [{"id": 18, "name": "Dramma"}, {"id": 80, "name": "Crime"}],
    "first_air_date": "2008-01-20",
}


@pytest.fixture
def tmdb(monkeypatch):
    async def fake_get(path, params=None, *, ttl=None):
        return dict(BREAKING_BAD)

    monkeypatch.setattr(watch_sync, "tmdb_get", fake_get)


@pytest.fixture
def user(client):
    register(client, "mario@example.com", "mario", "password123")
    return client


def watched_list(client):
    return client.get("/api/watched").json()


def test_un_episodio_basta_a_segnare_la_serie(user, tmdb):
    r = user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    assert r.status_code == 201 and r.json()["series"] == "added"

    rows = watched_list(user)
    assert len(rows) == 1
    assert rows[0]["tmdb_id"] == 1396 and rows[0]["media_type"] == "tv"
    assert rows[0]["title"] == "Breaking Bad"
    assert rows[0]["poster_path"] == "/bb.jpg"
    assert json.loads(rows[0]["genre_ids"]) == [18, 80]  # dal dettaglio TMDB: genres[].id


def test_serie_in_watchlist_viene_spostata(user, tmdb):
    user.post("/api/watchlist", json={"tmdb_id": 1396, "media_type": "tv", "title": "Breaking Bad"})

    r = user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    assert r.json()["series"] == "moved"

    assert [w["tmdb_id"] for w in watched_list(user)] == [1396]
    assert user.get("/api/watchlist").json() == []  # non resta in "Da vedere"


def test_serie_gia_vista_non_perde_voto_e_recensione(user, tmdb):
    user.post("/api/watched", json={"tmdb_id": 1396, "media_type": "tv", "title": "Breaking Bad", "rating": 10})
    user.patch("/api/watched/1396/tv", json={"review": "Capolavoro"})

    r = user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    assert r.json()["series"] == "already"

    row = watched_list(user)[0]
    assert row["rating"] == 10 and row["review"] == "Capolavoro"


def test_segnare_una_stagione_intera(user, tmdb):
    r = user.post("/api/progress/1396/season/1", json={"episode_numbers": [1, 2, 3]})
    assert r.status_code == 201
    assert r.json() == {"ok": True, "added": 3, "series": "added"}
    assert len(watched_list(user)) == 1


def test_riallinea_anche_le_serie_seguite_da_prima(user, tmdb):
    """Chi aveva già del progresso salvato entra nei visti al primo episodio segnato.

    Il primo mark crea la riga; toglierla a mano e rimarcare lo stesso episodio (che
    esiste già) deve ricrearla: il riallineamento non dipende dall'aver inserito
    davvero un episodio nuovo.
    """
    user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    user.delete("/api/watched/1396/tv")
    assert watched_list(user) == []

    r = user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    assert r.json()["series"] == "added"
    assert len(watched_list(user)) == 1


def test_togliere_gli_episodi_non_toglie_la_serie(user, tmdb):
    """Asimmetria voluta: nei "Visti" possono esserci voto e recensione da non buttare."""
    user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    user.delete("/api/progress/1396/episode/1/1")

    assert user.get("/api/progress/1396").json() == []
    assert [w["tmdb_id"] for w in watched_list(user)] == [1396]


def test_tmdb_giu_non_perde_il_progresso(user, monkeypatch):
    """Se TMDB non risponde l'episodio si salva lo stesso, la serie si segnerà dopo."""
    async def boom(path, params=None, *, ttl=None):
        raise RuntimeError("TMDB irraggiungibile")

    monkeypatch.setattr(watch_sync, "tmdb_get", boom)

    r = user.post("/api/progress/1396/episode", json={"season_number": 1, "episode_number": 1})
    assert r.status_code == 201 and r.json()["series"] == "skipped"
    assert user.get("/api/progress/1396").json() == [{"season_number": 1, "episode_number": 1}]
    assert watched_list(user) == []
