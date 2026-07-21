from .helpers import register


def _watch(client, **over):
    item = {"tmdb_id": 603, "media_type": "movie", "title": "The Matrix", "release_date": "1999-03-31"}
    item.update(over)
    return client.post("/api/watched", json=item)


def test_add_and_list(client):
    register(client, "mario@example.com", "mario", "password123")
    assert _watch(client, rating=9).status_code == 201
    rows = client.get("/api/watched").json()
    assert len(rows) == 1 and rows[0]["rating"] == 9


def test_partial_patch_keeps_other_fields(client):
    register(client, "mario@example.com", "mario", "password123")
    _watch(client, rating=9)
    # imposto recensione + data
    assert client.patch("/api/watched/603/movie", json={"review": "Bellissimo", "watched_on": "2026-07-01"}).status_code == 200
    row = client.get("/api/watched").json()[0]
    assert row["review"] == "Bellissimo" and row["watched_on"] == "2026-07-01"
    # cambiare solo il voto NON azzera la recensione
    assert client.patch("/api/watched/603/movie", json={"rating": 7}).status_code == 200
    row = client.get("/api/watched").json()[0]
    assert row["rating"] == 7 and row["review"] == "Bellissimo"


def test_export_includes_review_and_date(client):
    register(client, "mario@example.com", "mario", "password123")
    _watch(client, rating=8)
    client.patch("/api/watched/603/movie", json={"review": "Un classico", "watched_on": "2026-07-02"})
    r = client.get("/api/import/export")
    assert r.status_code == 200 and "text/csv" in r.headers.get("content-type", "")
    body = r.text
    assert "watched_on" in body and "review" in body  # header
    assert "Un classico" in body and "2026-07-02" in body and "The Matrix" in body
