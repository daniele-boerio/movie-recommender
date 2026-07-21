"""Genera notifiche in-app per gli episodi in arrivo delle serie tracciate.

La logica è isolata da scheduler e TMDB (riceve `db` e una funzione `fetch`), così è
testabile in-process senza rete né DB reale.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..models import Notification, Watched

# Finestra: notifichiamo un episodio che esce da poco (2 giorni) fino a due settimane avanti.
_PAST = timedelta(days=2)
_AHEAD = timedelta(days=14)


async def scan_new_episodes(db: Session, fetch) -> int:
    """Per ogni serie TV in watchlist/visti di qualcuno, se ha un prossimo episodio nella
    finestra, crea una notifica per ciascun utente che la traccia. Ritorna quante ne crea.

    `fetch(path)` è una coroutine che restituisce il JSON di TMDB (in prod: tmdb_get).
    """
    today = date.today()
    series_ids = [
        r[0]
        for r in db.query(Watched.tmdb_id)
        .filter(Watched.media_type == "tv")
        .distinct()
        .all()
    ]

    created = 0
    for tid in series_ids:
        try:
            data = await fetch(f"/tv/{tid}")
        except Exception:
            continue

        nxt = data.get("next_episode_to_air")
        if not nxt or not nxt.get("air_date"):
            continue
        try:
            air_d = date.fromisoformat(nxt["air_date"])
        except (ValueError, TypeError):
            continue
        if not (today - _PAST <= air_d <= today + _AHEAD):
            continue

        ref = f"S{nxt.get('season_number')}E{nxt.get('episode_number')}"
        ep_name = nxt.get("name")
        title = data.get("name") or "Serie TV"
        body = (
            f"Nuovo episodio {ref}"
            + (f": {ep_name}" if ep_name else "")
            + f" — in onda il {nxt['air_date']}"
        )
        poster = data.get("poster_path")

        # Tutti gli utenti che seguono questa serie (watchlist o visti).
        user_ids = [
            r[0]
            for r in db.query(Watched.user_id)
            .filter(Watched.tmdb_id == tid, Watched.media_type == "tv")
            .distinct()
            .all()
        ]
        for uid in user_ids:
            exists = (
                db.query(Notification)
                .filter(
                    Notification.user_id == uid,
                    Notification.tmdb_id == tid,
                    Notification.ref == ref,
                )
                .first()
            )
            if exists:
                continue
            db.add(
                Notification(
                    user_id=uid,
                    type="new_episode",
                    tmdb_id=tid,
                    media_type="tv",
                    title=title,
                    body=body,
                    ref=ref,
                    poster_path=poster,
                )
            )
            created += 1

    db.commit()
    return created
