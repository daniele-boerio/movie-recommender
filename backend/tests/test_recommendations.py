"""Consigli: filtri dell'utente e bilanciamento del punteggio.

TMDB è finto (`recommender.tmdb_get`): ogni titolo visto suggerisce sempre lo stesso
gruppo di candidati, così si vede esattamente cosa entra e cosa esce.
"""

import json

import pytest

from app.services import recommender as rec
from app.services.recommender import RecFilters

from .helpers import register

# Candidati suggeriti da TMDB per qualsiasi seed: un film d'azione, un cartone
# animato, un anime e una serie.
CANDIDATES = [
    {
        "id": 100, "title": "Blade Runner 2049", "media_type": "movie",
        "genre_ids": [878, 18], "vote_average": 7.6,
        "original_language": "en", "release_date": "2017-10-04",
    },
    {
        "id": 200, "title": "Spider-Man: New Generation", "media_type": "movie",
        "genre_ids": [16, 28, 12, 878], "vote_average": 8.4,
        "original_language": "en", "release_date": "2018-12-06",
    },
    {
        "id": 300, "title": "Cowboy Bebop", "media_type": "tv",
        "genre_ids": [16, 28, 878], "vote_average": 8.6,
        "original_language": "ja", "first_air_date": "1998-04-03",
    },
    {
        "id": 400, "title": "Daredevil", "media_type": "tv",
        "genre_ids": [28, 18], "vote_average": 8.0,
        "original_language": "en", "first_air_date": "2015-04-10",
    },
]


@pytest.fixture
def tmdb(monkeypatch):
    async def fake_get(path, params=None, *, ttl=None):
        return {"results": [dict(c) for c in CANDIDATES]}

    monkeypatch.setattr(rec, "tmdb_get", fake_get)


@pytest.fixture
def user(client):
    """Un utente con un film Marvel visto (azione, avventura, fantascienza)."""
    register(client, "mario@example.com", "mario", "password123")
    client.post("/api/watched", json={
        "tmdb_id": 24428,
        "media_type": "movie",
        "title": "The Avengers",
        "rating": 9,
        "genre_ids": json.dumps([28, 12, 878]),
    })
    return client


def ids(data):
    return [r["tmdb_id"] for r in data["results"]]


def test_senza_filtri_arrivano_tutti(user, tmdb):
    data = user.get("/api/recommendations").json()
    assert sorted(ids(data)) == [100, 200, 300, 400]
    assert data["filtered"] is False


def test_escludere_animazione_toglie_cartoni_e_anime(user, tmdb):
    """Il caso che ha fatto nascere i filtri: solo cartoni Marvel tra i consigli."""
    data = user.get("/api/recommendations", params={"exclude_genres": "16"}).json()
    assert sorted(ids(data)) == [100, 400]
    assert data["filtered"] is True


def test_escludere_gli_anime_lascia_i_cartoni_occidentali(user, tmdb):
    """"Niente anime" ≠ "niente animazione": Spider-Man resta, Cowboy Bebop no."""
    data = user.get("/api/recommendations", params={"exclude_anime": "true"}).json()
    assert sorted(ids(data)) == [100, 200, 400]


def test_filtri_combinati(user, tmdb):
    data = user.get("/api/recommendations", params={
        "media_type": "movie", "min_vote": 8, "year_from": 2018,
    }).json()
    assert ids(data) == [200]  # Blade Runner è del 2017, le serie sono escluse dal tipo


def test_il_filtro_agisce_prima_del_taglio(user, tmdb):
    """Filtrare *dopo* i primi N lascerebbe la pagina mezza vuota."""
    tutti = user.get("/api/recommendations", params={"limit": 2}).json()
    assert len(tutti["results"]) == 2

    # Anche escludendo i due candidati animati, i posti richiesti restano pieni.
    filtrati = user.get("/api/recommendations", params={"limit": 2, "exclude_genres": "16"}).json()
    assert sorted(ids(filtrati)) == [100, 400]


def test_generi_non_numerici_ignorati(user, tmdb):
    """"16,pippo," non deve dare 422: si tiene il 16 e si butta il resto."""
    r = user.get("/api/recommendations", params={"exclude_genres": "16,pippo,"})
    assert r.status_code == 200
    assert sorted(ids(r.json())) == [100, 400]


def test_il_profilo_generi_non_schiaccia_gli_altri_segnali(user, tmdb):
    """Un candidato etichettato con mezzo catalogo non deve vincere per quello.

    Spider-Man ha 4 generi (3 dei quali preferiti) e voto più alto di Daredevil, che ne
    ha 2: è giusto che vinca. Ma il divario deve restare nell'ordine di grandezza degli
    altri segnali, non decuplicarli — era il difetto che riempiva i consigli di cartoni.
    """
    results = {r["tmdb_id"]: r["score"] for r in user.get("/api/recommendations").json()["results"]}
    assert abs(results[200] - results[400]) < 10


def test_filtro_scarta_i_titoli_senza_data_solo_se_serve():
    """Senza data di uscita non si può dire che stia nel range richiesto."""
    senza_data = {"genre_ids": [28], "vote_average": 7, "release_date": ""}
    assert RecFilters().accepts(senza_data, "movie") is True
    assert RecFilters(year_from=2000).accepts(senza_data, "movie") is False
