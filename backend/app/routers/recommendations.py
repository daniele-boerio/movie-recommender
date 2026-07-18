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
    # Seed: solo i titoli VISTI (non la watchlist: quelli non li ho ancora guardati,
    # non dicono nulla sui miei gusti). order_by esplicito: Postgres non garantisce un
    # ordine senza, e il motore campiona i primi 30. Così il campione è "i 30 più recenti".
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id, Watched.status == "watched")
        .order_by(Watched.added_at.desc())
        .all()
    )
    # Esclusione: tutto ciò che è già in lista (visti + da vedere). Consigliare un titolo
    # già salvato in watchlist è inutile: l'utente l'ha già scelto.
    saved = (
        db.query(Watched.tmdb_id, Watched.media_type)
        .filter(Watched.user_id == user_id)
        .all()
    )
    exclude = {(tmdb_id, media_type) for tmdb_id, media_type in saved}
    return await build_recommendations(rows, limit, exclude=exclude)
