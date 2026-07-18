"""Statistiche personali, calcolate dalla lista 'Visti' dell'utente corrente.

Solo lettura e solo DB: i nomi dei generi li risolve il frontend (che i generi li ha
già caricati), così qui non servono chiamate a TMDB.
"""

import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched

router = APIRouter(prefix="/api", tags=["Stats"])


def _last_months(n: int = 12) -> list[str]:
    """Le ultime n etichette 'YYYY-MM', dalla più vecchia alla più recente."""
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id, Watched.status == "watched")
        .all()
    )

    movie = sum(1 for r in rows if r.media_type == "movie")
    tv = sum(1 for r in rows if r.media_type == "tv")

    ratings = [r.rating for r in rows if r.rating]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    top = max((r for r in rows if r.rating), key=lambda r: r.rating, default=None)
    top_rated = (
        {
            "tmdb_id": top.tmdb_id,
            "media_type": top.media_type,
            "title": top.title,
            "poster_path": top.poster_path,
            "rating": top.rating,
        }
        if top
        else None
    )

    genre_counter: Counter = Counter()
    for r in rows:
        if r.genre_ids:
            try:
                for g in json.loads(r.genre_ids):
                    genre_counter[g] += 1
            except (json.JSONDecodeError, TypeError):
                pass
    genres = [{"genre_id": gid, "count": c} for gid, c in genre_counter.most_common(8)]

    month_counter: Counter = Counter()
    for r in rows:
        if r.added_at:
            month_counter[r.added_at.strftime("%Y-%m")] += 1
    timeline = [{"month": mth, "count": month_counter.get(mth, 0)} for mth in _last_months(12)]

    return {
        "total": {"movie": movie, "tv": tv, "all": movie + tv},
        "avg_rating": avg_rating,
        "rated_count": len(ratings),
        "top_rated": top_rated,
        "genres": genres,
        "timeline": timeline,
    }
