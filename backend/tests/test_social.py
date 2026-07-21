from .helpers import new_user, register


def test_search_follow_and_profile(client):
    register(client, "mario@example.com", "mario", "password123")
    new_user("lucia@example.com", "lucia", "passwordlucia1")

    assert any(u["username"] == "lucia" for u in client.get("/api/users/search?q=luc").json())
    assert client.post("/api/users/lucia/follow").status_code == 201
    assert client.post("/api/users/lucia/follow").status_code == 201  # idempotente
    assert client.post("/api/users/mario/follow").status_code == 400  # no self-follow

    prof = client.get("/api/users/lucia").json()
    assert prof["is_following"] is True and prof["followers"] == 1

    assert client.request("DELETE", "/api/users/lucia/follow").status_code == 200
    assert client.get("/api/users/lucia").json()["is_following"] is False
    assert client.get("/api/users/nessuno").status_code == 404


def test_feed_reflects_follows(client):
    register(client, "mario@example.com", "mario", "password123")
    lucia = new_user("lucia@example.com", "lucia", "passwordlucia1")
    lucia.post("/api/watched", json={"tmdb_id": 27205, "media_type": "movie", "title": "Inception", "rating": 8})

    client.post("/api/users/lucia/follow")
    assert any(e["username"] == "lucia" and e["title"] == "Inception" for e in client.get("/api/social/feed").json())
    client.request("DELETE", "/api/users/lucia/follow")
    assert not any(e["username"] == "lucia" for e in client.get("/api/social/feed").json())


def test_compatibility(client):
    register(client, "mario@example.com", "mario", "password123")
    client.post("/api/watched", json={"tmdb_id": 603, "media_type": "movie", "title": "The Matrix", "rating": 7})
    lucia = new_user("lucia@example.com", "lucia", "passwordlucia1")
    lucia.post("/api/watched", json={"tmdb_id": 603, "media_type": "movie", "title": "The Matrix", "rating": 9})

    comp = client.get("/api/users/lucia").json()["compatibility"]
    assert comp["common"] == 1 and isinstance(comp["score"], int)


def test_followers_and_mutual(client):
    register(client, "mario@example.com", "mario", "password123")
    lucia = new_user("lucia@example.com", "lucia", "passwordlucia1")

    # lucia segue mario → mario ha 1 follower, non reciproco
    lucia.post("/api/users/mario/follow")
    followers = client.get("/api/social/followers").json()
    assert len(followers) == 1 and followers[0]["username"] == "lucia" and followers[0]["following"] is False

    # mario segue lucia → reciproco su entrambe le liste
    client.post("/api/users/lucia/follow")
    assert client.get("/api/social/followers").json()[0]["following"] is True
    assert client.get("/api/social/following").json()[0]["mutual"] is True
