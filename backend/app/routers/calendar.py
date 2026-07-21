"""Calendario delle uscite imminenti per i titoli in watchlist.

Per ogni titolo "da vedere" chiediamo a TMDB la data utile: per i film la data d'uscita
(se futura), per le serie il prossimo episodio in onda. Le chiamate partono in parallelo
(asyncio.gather) così l'attesa è quella della più lenta, non la somma.
"""

import asyncio
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..tmdb import tmdb_get

router = APIRouter(prefix="/api", tags=["Calendar"])


async def _event_for(row: Watched, today: str) -> dict | None:
    try:
        data = await tmdb_get(f"/{row.media_type}/{row.tmdb_id}")
    except Exception:
        return None

    if row.media_type == "movie":
        rd = data.get("release_date")
        # Solo uscite ancora da venire: il confronto tra stringhe ISO "YYYY-MM-DD" ordina
        # come le date.
        if not rd or rd < today:
            return None
        return {
            "tmdb_id": row.tmdb_id,
            "media_type": "movie",
            "title": data.get("title") or row.title,
            "poster_path": data.get("poster_path") or row.poster_path,
            "date": rd,
            "label": "Uscita al cinema",
        }

    # Serie: il prossimo episodio programmato (None se è finita o in pausa).
    nxt = data.get("next_episode_to_air")
    if not nxt or not nxt.get("air_date"):
        return None
    season = nxt.get("season_number")
    episode = nxt.get("episode_number")
    name = nxt.get("name")
    label = f"S{season}E{episode}" + (f" · {name}" if name else "")
    return {
        "tmdb_id": row.tmdb_id,
        "media_type": "tv",
        "title": data.get("name") or row.title,
        "poster_path": data.get("poster_path") or row.poster_path,
        "date": nxt["air_date"],
        "label": label,
    }


@router.get("/calendar")
async def calendar(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id, Watched.status == "watchlist")
        .limit(60)  # tetto alle chiamate TMDB in un colpo solo
        .all()
    )
    today = date.today().isoformat()
    events = await asyncio.gather(*[_event_for(r, today) for r in rows])
    events = [e for e in events if e]
    events.sort(key=lambda e: e["date"])
    return {"events": events}
