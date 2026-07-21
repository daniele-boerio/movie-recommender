from fastapi.testclient import TestClient

from app import main
from app.models import User, Watched

from .helpers import CODE, register


def _fresh():
    return TestClient(main.app)


def test_register_and_me(client):
    register(client, "mario@example.com", "mario", "password123")
    assert client.get("/api/auth/me").json()["email"] == "mario@example.com"


def test_login_wrong_and_right(client):
    register(client, "mario@example.com", "mario", "password123")
    fresh = _fresh()
    assert fresh.post("/api/auth/login", json={"identifier": "mario", "password": "sbagliata"}).status_code == 401
    assert fresh.post("/api/auth/login", json={"identifier": "mario", "password": "password123"}).status_code == 200


def test_change_password_invalidates_old(client):
    register(client, "mario@example.com", "mario", "password123")
    assert client.post("/api/auth/change-password", json={"current_password": "x", "new_password": "nuova123456"}).status_code == 400
    assert client.post("/api/auth/change-password", json={"current_password": "password123", "new_password": "nuova123456"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200  # sessione corrente viva

    fresh = _fresh()
    assert fresh.post("/api/auth/login", json={"identifier": "mario", "password": "password123"}).status_code == 401
    assert fresh.post("/api/auth/login", json={"identifier": "mario", "password": "nuova123456"}).status_code == 200


def test_password_reset(client):
    register(client, "mario@example.com", "mario", "password123")
    assert client.post("/api/auth/password-reset/request", json={"email": "mario@example.com"}).status_code == 200
    assert client.post(
        "/api/auth/password-reset/confirm",
        json={"email": "mario@example.com", "code": CODE, "new_password": "reset123456"},
    ).status_code == 200
    assert client.post("/api/auth/password-reset/request", json={"email": "nobody@example.com"}).status_code == 200  # neutra

    fresh = _fresh()
    assert fresh.post("/api/auth/login", json={"identifier": "mario", "password": "password123"}).status_code == 401
    assert fresh.post("/api/auth/login", json={"identifier": "mario", "password": "reset123456"}).status_code == 200


def test_delete_account_cascade(client, db):
    register(client, "mario@example.com", "mario", "password123")
    uid = client.get("/api/auth/me").json()["id"]
    client.post("/api/watched", json={"tmdb_id": 603, "media_type": "movie", "title": "The Matrix"})

    assert client.request("DELETE", "/api/auth/account", json={"password": "sbagliata"}).status_code == 400
    assert client.request("DELETE", "/api/auth/account", json={"password": "password123"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    assert db.query(User).filter(User.id == uid).count() == 0
    assert db.query(Watched).filter(Watched.user_id == uid).count() == 0  # cascata
