"""Raccomandazioni personalizzate, calcolate sulla lista dell'utente corrente."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..services.recommender import RecFilters, build_recommendations

router = APIRouter(prefix="/api", tags=["Recommendations"])


def _genre_ids(raw: str | None) -> frozenset[int]:
    """"16,99" → {16, 99}. Gli id non numerici li ignoriamo invece di dare 422."""
    if not raw:
        return frozenset()
    return frozenset(int(p) for p in raw.split(",") if p.strip().lstrip("-").isdigit())


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(20, ge=1, le=50),
    media_type: str = Query("all", pattern="^(movie|tv|all)$"),
    exclude_genres: str | None = Query(None, description="id dei generi da escludere, separati da virgola"),
    exclude_anime: bool = Query(False, description="scarta l'animazione giapponese"),
    min_vote: float = Query(0, ge=0, le=10),
    year_from: int | None = Query(None, ge=1900, le=2100),
    year_to: int | None = Query(None, ge=1900, le=2100),
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
    exclude = {(tmdb_id, mt) for tmdb_id, mt in saved}

    filters = RecFilters(
        media_type=media_type,
        exclude_genres=_genre_ids(exclude_genres),
        exclude_anime=exclude_anime,
        min_vote=min_vote,
        year_from=year_from,
        year_to=year_to,
    )
    return await build_recommendations(rows, limit, exclude=exclude, filters=filters)
