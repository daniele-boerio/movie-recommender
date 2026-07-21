import asyncio
from datetime import date, timedelta

from app.services.notifier import scan_new_episodes

from .conftest import TestingSession
from .helpers import register


async def _fake_fetch(path):
    return {
        "name": "Game of Thrones",
        "poster_path": "/got.jpg",
        "next_episode_to_air": {
            "air_date": (date.today() + timedelta(days=3)).isoformat(),
            "season_number": 8,
            "episode_number": 6,
            "name": "The Iron Throne",
        },
    }


async def _fake_fetch_far(path):
    # episodio troppo in là nel tempo: fuori finestra, nessuna notifica
    return {
        "name": "Foundation",
        "next_episode_to_air": {
            "air_date": (date.today() + timedelta(days=90)).isoformat(),
            "season_number": 3,
            "episode_number": 1,
        },
    }


def test_scan_creates_and_dedups(client):
    register(client, "mario@example.com", "mario", "password123")
    client.post("/api/watched", json={"tmdb_id": 1399, "media_type": "tv", "title": "Game of Thrones", "status": "watched"})

    db = TestingSession()
    assert asyncio.run(scan_new_episodes(db, _fake_fetch)) == 1
    db.close()
    # seconda passata: idempotente
    db = TestingSession()
    assert asyncio.run(scan_new_episodes(db, _fake_fetch)) == 0
    db.close()

    nots = client.get("/api/notifications").json()
    assert len(nots) == 1 and "S8E6" in nots[0]["body"] and nots[0]["read"] is False
    assert client.get("/api/notifications/unread-count").json()["count"] == 1
    client.post("/api/notifications/read")
    assert client.get("/api/notifications/unread-count").json()["count"] == 0


def test_scan_ignores_far_episodes(client):
    register(client, "mario@example.com", "mario", "password123")
    client.post("/api/watched", json={"tmdb_id": 93740, "media_type": "tv", "title": "Foundation"})
    db = TestingSession()
    assert asyncio.run(scan_new_episodes(db, _fake_fetch_far)) == 0
    db.close()
