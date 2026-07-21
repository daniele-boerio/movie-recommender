"""Utility per i test: creazione utenti autenticati."""

from fastapi.testclient import TestClient

from app import main

CODE = "ABCDEF"  # coincide con la patch di auth.generate_code in conftest


def register(client, email, username, password):
    client.post("/api/auth/register/request", json={"email": email})
    r = client.post(
        "/api/auth/register",
        json={"email": email, "code": CODE, "username": username, "password": password},
    )
    assert r.status_code == 201, r.text
    return r


def new_user(email, username, password):
    """Un client TestClient nuovo (cookie propri) già loggato come l'utente creato."""
    c = TestClient(main.app)
    register(c, email, username, password)
    return c
