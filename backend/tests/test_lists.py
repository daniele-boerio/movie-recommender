from .helpers import new_user, register


def test_crud_and_duplicate(client):
    register(client, "mario@example.com", "mario", "password123")
    lid = client.post("/api/lists", json={"name": "Preferiti"}).json()["id"]
    assert client.post(f"/api/lists/{lid}/items", json={"tmdb_id": 603, "media_type": "movie", "title": "The Matrix"}).status_code == 201
    assert client.post(f"/api/lists/{lid}/items", json={"tmdb_id": 603, "media_type": "movie", "title": "The Matrix"}).status_code == 409
    assert len(client.get(f"/api/lists/{lid}").json()["items"]) == 1
    assert client.patch(f"/api/lists/{lid}", json={"name": "Top"}).status_code == 200
    assert client.request("DELETE", f"/api/lists/{lid}/items/603/movie").status_code == 200
    assert client.request("DELETE", f"/api/lists/{lid}").status_code == 200


def test_ownership_isolation(client):
    register(client, "mario@example.com", "mario", "password123")
    lid = client.post("/api/lists", json={"name": "Mia"}).json()["id"]
    lucia = new_user("lucia@example.com", "lucia", "passwordlucia1")
    assert lucia.get(f"/api/lists/{lid}").status_code == 404
    assert lucia.request("DELETE", f"/api/lists/{lid}").status_code == 404


def test_shared_list_flow_and_notifications(client):
    register(client, "mario@example.com", "mario", "password123")
    lucia = new_user("lucia@example.com", "lucia", "passwordlucia1")
    lucia_id = lucia.get("/api/auth/me").json()["id"]

    lid = client.post("/api/lists", json={"name": "Serata"}).json()["id"]
    assert client.post(f"/api/lists/{lid}/members", json={"username": "lucia"}).status_code == 201
    # invito → notifica per lucia
    assert any(n["type"] == "list_invite" for n in lucia.get("/api/notifications").json())
    # lucia vede la lista come non-owner
    assert any(x["id"] == lid and x["is_owner"] is False for x in lucia.get("/api/lists").json())
    # lucia (membro) può aggiungere; il proprietario riceve la notifica
    assert lucia.post(f"/api/lists/{lid}/items", json={"tmdb_id": 550, "media_type": "movie", "title": "Fight Club"}).status_code == 201
    assert any(n["type"] == "list_item" and "Fight Club" in n["body"] for n in client.get("/api/notifications").json())
    # ma non può rinominare (solo owner)
    assert lucia.patch(f"/api/lists/{lid}", json={"name": "Hack"}).status_code == 404
    # lucia lascia la lista
    assert lucia.request("DELETE", f"/api/lists/{lid}/members/{lucia_id}").status_code == 200
    assert not any(x["id"] == lid for x in lucia.get("/api/lists").json())


def test_elenco_liste_conteggi_anteprima_e_condivisione(client):
    """GET /api/lists con le query aggregate: stessi numeri di prima, per ogni lista."""
    register(client, "mario@example.com", "mario", "password123")
    new_user("lucia@example.com", "lucia", "passwordlucia1")

    piena = client.post("/api/lists", json={"name": "Piena"}).json()["id"]
    vuota = client.post("/api/lists", json={"name": "Vuota"}).json()["id"]
    for i in range(6):
        client.post(
            f"/api/lists/{piena}/items",
            json={
                "tmdb_id": 100 + i,
                "media_type": "movie",
                "title": f"Film {i}",
                # il penultimo aggiunto è senza copertina: resta fuori dall'anteprima
                "poster_path": None if i == 4 else f"/p{i}.jpg",
            },
        )
    client.post(f"/api/lists/{piena}/members", json={"username": "lucia"})

    by_id = {x["id"]: x for x in client.get("/api/lists").json()}
    assert by_id[piena]["count"] == 6
    assert by_id[piena]["shared"] is True
    # le 4 più recenti (5, 4, 3, 2) meno quella senza copertina
    assert set(by_id[piena]["preview"]) == {"/p5.jpg", "/p3.jpg", "/p2.jpg"}
    assert by_id[vuota] == {
        "id": vuota, "name": "Vuota", "count": 0, "preview": [], "is_owner": True, "shared": False,
    }
