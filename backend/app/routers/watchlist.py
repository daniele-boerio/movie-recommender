"""CRUD della watchlist "Da vedere".

È la stessa tabella `watched`, distinta dalle righe `status == 'watchlist'`. Lo spostamento
"da vedere" → "visto" NON sta qui: lo fa POST /api/watched, che se il titolo è già in
watchlist ne cambia solo lo status (vedi routers/watched.py).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..schemas import WatchedItem
from .watched import _serialize  # stessa serializzazione della lista visti

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


@router.get("")
async def get_watchlist(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """La watchlist dell'utente corrente, dalla più recente."""
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id, Watched.status == "watchlist")
        .order_by(Watched.added_at.desc())
        .all()
    )
    return [_serialize(w) for w in rows]


@router.post("", status_code=201)
async def add_watchlist(
    item: WatchedItem,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Aggiunge un titolo alla watchlist "Da vedere"."""
    existing = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == item.tmdb_id,
            Watched.media_type == item.media_type,
        )
        .first()
    )
    if existing:
        # Un titolo già visto non va nella lista dei "da vedere": messaggi distinti
        # così il frontend può spiegare all'utente perché non è stato aggiunto.
        if existing.status == "watched":
            raise HTTPException(409, "Già nei tuoi visti")
        raise HTTPException(409, 'Già in "Da vedere"')

    db.add(Watched(user_id=user_id, status="watchlist", **item.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Già nella lista")
    return {"ok": True}


@router.delete("/{tmdb_id}/{media_type}")
async def remove_watchlist(
    tmdb_id: int,
    media_type: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Rimuove un titolo dalla watchlist dell'utente corrente."""
    deleted = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == tmdb_id,
            Watched.media_type == media_type,
            Watched.status == "watchlist",
        )
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, 'Non trovato in "Da vedere"')
    return {"ok": True}
