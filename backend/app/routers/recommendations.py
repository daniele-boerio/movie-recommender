"""Raccomandazioni personalizzate, calcolate sulla lista dell'utente corrente."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..services.recommender import build_recommendations

router = APIRouter(prefix="/api", tags=["Recommendations"])


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # order_by esplicito: Postgres non garantisce un ordine senza, e il motore
    # campiona i primi 30 titoli. Così il campione è "i 30 più recenti", stabile.
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id)
        .order_by(Watched.added_at.desc())
        .all()
    )
    return await build_recommendations(rows, limit)
