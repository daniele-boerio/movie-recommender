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


def test_studi_omonimi_ci_stanno_tutti(client, tmdb):
    """«disney» deve pescare Walt Disney Pictures, non solo le etichette minori.

    Ordinando per il nostro punteggio, "Disney Channel" (il nome *comincia* con la query)
    scavalcava "Walt Disney Pictures" (la query è dentro il nome) e con un tetto basso lo
    studio principale restava fuori. Per gli studi teniamo l'ordine di TMDB.
    """
    tmdb.routes["/search/multi"] = {"results": [], "total_pages": 1}
    tmdb.routes["/search/company"] = {
        "results": [
            {"id": 2, "name": "Walt Disney Pictures"},
            {"id": 5, "name": "Disney Channel"},
            {"id": 6, "name": "Disneynature"},
            {"id": 3, "name": "Walt Disney Animation Studios"},
            {"id": 99, "name": "Pixar"},  # non contiene "disney": scartata
        ]
    }
    tmdb.routes["/discover/movie"] = lambda p: {
        "results": [movie(1, "Il Re Leone", 40)] if "2" in p.get("with_companies", "") else [],
        "total_pages": 1,
    }

    data = client.get("/api/search", params={"q": "disney"}).json()

    names = [c["name"] for c in data["matched"]["companies"]]
    assert names == [
        "Walt Disney Pictures",
        "Disney Channel",
        "Disneynature",
        "Walt Disney Animation Studios",
    ]
    assert [it["id"] for it in data["results"]] == [1]


# ── Filtri e ordinamento ────────────────────────────────────────────────────────
# Il nodo è che devono valere su *tutte* le pagine e su tutte le fonti, non solo sul
# primo lotto: filtrare lato client svuotava le pagine e rimescolava l'ordine.

def _pool_routes(tmdb, items):
    """TMDB finto che pagina davvero: 20 elementi per pagina, come quello vero."""
    tmdb.routes["/search/multi"] = lambda p: {"results": [], "total_pages": 1}
    tmdb.routes["/search/company"] = {"results": [{"id": 1, "name": "Studio Test"}]}
    tmdb.routes["/discover/movie"] = lambda p: {
        "results": items[(p.get("page", 1) - 1) * 20: p.get("page", 1) * 20],
        "total_pages": 25,
    }
    tmdb.routes["/discover/tv"] = {"results": [], "total_pages": 1}


def test_il_filtro_anno_vale_su_tutte_le_pagine(client, tmdb):
    """Il caso segnalato: filtrando per data, dal secondo lotto rispuntava altro."""
    # 60 film alternati dentro/fuori l'intervallo, sparsi su 3 pagine TMDB.
    items = [
        movie(i, f"Film {i}", 100 - i, release_date=f"{1990 + (i % 40)}-01-01")
        for i in range(60)
    ]
    _pool_routes(tmdb, items)

    data = client.get(
        "/api/search", params={"q": "studio test", "year_from": 2015, "year_to": 2020}
    ).json()

    anni = [int(it["release_date"][:4]) for it in data["results"]]
    assert anni, "il filtro non deve svuotare i risultati"
    assert all(2015 <= a <= 2020 for a in anni)
    # Il serbatoio è stato filtrato prima di impaginare: total_pages è quello vero.
    assert data["total_pages"] == 1


def test_ordinamento_per_data_e_globale_non_per_lotto(client, tmdb):
    """Pagina 2 deve *proseguire* la classifica di pagina 1, non ricominciarla."""
    items = [
        movie(i, f"Film {i}", 1, release_date=f"{1960 + i}-01-01")
        for i in range(60)
    ]
    _pool_routes(tmdb, items)

    p1 = client.get("/api/search", params={"q": "studio test", "sort_by": "date.desc"}).json()
    p2 = client.get(
        "/api/search", params={"q": "studio test", "sort_by": "date.desc", "page": 2}
    ).json()

    date1 = [it["release_date"] for it in p1["results"]]
    date2 = [it["release_date"] for it in p2["results"]]

    assert date1 == sorted(date1, reverse=True)
    assert date2 == sorted(date2, reverse=True)
    assert min(date1) >= max(date2)  # nessun titolo più recente ricompare dopo


def test_voto_minimo_e_genere(client, tmdb):
    items = [
        movie(1, "Brutto", 5, vote_average=4.0, genre_ids=[28]),
        movie(2, "Bello", 5, vote_average=8.5, genre_ids=[28]),
        movie(3, "Bello ma altro genere", 5, vote_average=9.0, genre_ids=[35]),
    ]
    _pool_routes(tmdb, items)

    data = client.get(
        "/api/search", params={"q": "studio test", "vote_min": 7, "genres": "28"}
    ).json()
    assert [it["id"] for it in data["results"]] == [2]


def test_lingua_originale_per_gli_anime(client, tmdb):
    items = [
        movie(1, "Cartone americano", 9, genre_ids=[16], original_language="en"),
        movie(2, "Anime", 8, genre_ids=[16], original_language="ja"),
    ]
    _pool_routes(tmdb, items)

    data = client.get(
        "/api/search", params={"q": "studio test", "genres": "16", "original_language": "ja"}
    ).json()
    assert [it["id"] for it in data["results"]] == [2]


def test_senza_filtri_niente_serbatoio_profondo(client, tmdb):
    """La modalità profonda costa ~20 chiamate: si accende solo se serve."""
    _pool_routes(tmdb, [movie(1, "Uno")])
    client.get("/api/search", params={"q": "studio test"})
    assert tmdb.calls.count("/discover/movie") == 1

    tmdb.calls.clear()
    client.get("/api/search", params={"q": "studio test", "year_from": 2000})
    assert tmdb.calls.count("/discover/movie") == 3  # una per pagina del serbatoio


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
