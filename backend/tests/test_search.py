"""Ricerca intelligente: oltre al titolo capisce persone, studi e temi.

TMDB è finto: `smart_search.tmdb_get` viene sostituito da un router di percorsi, così i
test provano la logica di riconoscimento, di unione e di ordinamento senza rete.
"""

import pytest

from app.services import smart_search as ss


@pytest.fixture
def tmdb(monkeypatch):
    """Sostituisce tmdb_get con un finto instradatore; registra i percorsi chiamati."""
    routes: dict = {}
    calls: list = []

    async def fake_get(path, params=None, *, ttl=None):
        calls.append(path)
        handler = routes.get(path)
        data = handler(params or {}) if callable(handler) else handler
        return data if data is not None else {"results": [], "total_pages": 1}

    monkeypatch.setattr(ss, "tmdb_get", fake_get)
    return type("Tmdb", (), {"routes": routes, "calls": calls})()


def movie(id, title, popularity=1.0, **extra):
    return {"id": id, "title": title, "popularity": popularity, **extra}


def test_studio_tema_e_persona_si_uniscono_ai_titoli(client, tmdb):
    """«marvel» deve dare i film Marvel, non solo i titoli con "marvel" dentro."""
    tmdb.routes["/search/multi"] = {
        "results": [{"id": 1, "media_type": "movie", "title": "Captain Marvel"}],
        "total_pages": 1,
    }
    tmdb.routes["/search/person"] = {
        "results": [{"id": 50, "name": "Elizabeth Marvel", "known_for_department": "Acting"}]
    }
    tmdb.routes["/search/company"] = {
        "results": [
            {"id": 420, "name": "Marvel Studios"},
            {"id": 7505, "name": "Marvel Entertainment"},
            {"id": 174, "name": "Warner Bros. Pictures"},  # non c'entra: va scartata
        ]
    }
    tmdb.routes["/search/keyword"] = {
        "results": [
            {"id": 180547, "name": "marvel cinematic universe"},
            {"id": 9715, "name": "superhero"},  # non contiene la query: scartata
        ]
    }
    tmdb.routes["/person/50/combined_credits"] = {
        "cast": [{"id": 60, "media_type": "movie", "title": "Lincoln", "popularity": 9}],
        "crew": [],
    }
    tmdb.routes["/discover/movie"] = lambda p: {
        "results": (
            # Captain Marvel torna anche qui: è già nei titoli, non va duplicato.
            [movie(1, "Captain Marvel", 30), movie(2, "Avengers", 20)]
            if "with_companies" in p
            else [movie(3, "Iron Man", 25)]
        ),
        "total_pages": 12,
    }

    r = client.get("/api/search", params={"q": "marvel"})
    assert r.status_code == 200, r.text
    data = r.json()

    # Le entità riconosciute: solo quelle che corrispondono davvero alla query.
    assert [c["name"] for c in data["matched"]["companies"]] == [
        "Marvel Studios",
        "Marvel Entertainment",
    ]
    assert [k["name"] for k in data["matched"]["keywords"]] == ["marvel cinematic universe"]
    assert data["matched"]["people"][0]["name"] == "Elizabeth Marvel"

    # Ordine: titoli → studio (match forte) → tema → persona (match debole).
    assert [it["id"] for it in data["results"]] == [1, 2, 3, 60]
    assert data["total_pages"] == 12

    # Lo studio riconosciuto viene interrogato con tutti i suoi id in OR.
    assert "/discover/movie" in tmdb.calls


def test_regista_porta_i_film_che_ha_diretto(client, tmdb):
    """«nolan» → la filmografia di Nolan, regia e recitazione, non i ringraziamenti."""
    tmdb.routes["/search/multi"] = {"results": [], "total_pages": 1}
    tmdb.routes["/search/person"] = {
        "results": [{"id": 525, "name": "Christopher Nolan", "known_for_department": "Directing"}]
    }
    tmdb.routes["/person/525/combined_credits"] = {
        "cast": [{"id": 10, "media_type": "movie", "title": "Cameo", "popularity": 5}],
        "crew": [
            {"id": 11, "media_type": "movie", "title": "Oppenheimer", "job": "Director", "popularity": 50},
            {"id": 12, "media_type": "movie", "title": "Un film qualsiasi", "job": "Thanks", "popularity": 99},
        ],
    }

    data = client.get("/api/search", params={"q": "nolan"}).json()

    assert data["matched"]["people"][0]["known_for_department"] == "Directing"
    assert [it["id"] for it in data["results"]] == [11, 10]  # per popolarità, senza "Thanks"


def test_filtro_su_film_non_tocca_le_serie(client, tmdb):
    """Con media_type=movie non ha senso interrogare /discover/tv."""
    tmdb.routes["/search/movie"] = {"results": [], "total_pages": 1}
    tmdb.routes["/search/company"] = {"results": [{"id": 3, "name": "Pixar"}]}
    tmdb.routes["/discover/movie"] = {"results": [movie(7, "Up")], "total_pages": 1}

    data = client.get("/api/search", params={"q": "pixar", "media_type": "movie"}).json()

    assert "/discover/tv" not in tmdb.calls
    assert [it["id"] for it in data["results"]] == [7]
    assert data["results"][0]["media_type"] == "movie"


def test_query_cortissima_non_espande(client, tmdb):
    """Sotto i 3 caratteri l'espansione sarebbe solo rumore (e otto chiamate a TMDB)."""
    tmdb.routes["/search/multi"] = {
        "results": [{"id": 1, "media_type": "movie", "title": "Up"}],
        "total_pages": 1,
    }

    data = client.get("/api/search", params={"q": "up"}).json()

    assert tmdb.calls == ["/search/multi"]
    assert data["matched"] == {"people": [], "companies": [], "keywords": []}


def test_smart_disattivabile(client, tmdb):
    """`smart=false` torna alla sola ricerca per titolo."""
    tmdb.routes["/search/multi"] = {
        "results": [{"id": 1, "media_type": "movie", "title": "Captain Marvel"}],
        "total_pages": 1,
    }

    data = client.get("/api/search", params={"q": "marvel", "smart": "false"}).json()

    assert tmdb.calls == ["/search/multi"]
    assert [it["id"] for it in data["results"]] == [1]


@pytest.mark.parametrize(
    "name, query, expected",
    [
        ("Christopher Nolan", "christopher nolan", 3),
        ("Christopher Nolan", "nolan", 1),
        ("Robert Downey Jr.", "robert downey", 2),
        ("Bong Joon-ho", "BONG JOON-HO", 3),
        ("Marvel Studios", "marvel", 2),
        ("Warner Bros. Pictures", "marvel", 0),
        ("Martina Rossi", "mar", 0),  # prefissi corti: troppo laschi, nessun match
    ],
)
def test_punteggio_di_pertinenza(name, query, expected):
    assert ss._score(name, query) == expected
