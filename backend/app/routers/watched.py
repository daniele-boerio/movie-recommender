"""CRUD della lista "Visti". Ogni riga appartiene a un utente."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..schemas import RatingUpdate, WatchedItem

router = APIRouter(prefix="/api/watched", tags=["Watched"])


def _serialize(w: Watched) -> dict:
    """Il frontend si aspetta le stesse chiavi di prima. user_id non esce: è un
    dettaglio interno, il client vede solo la propria roba per definizione."""
    return {
        "id": w.id,
        "tmdb_id": w.tmdb_id,
        "media_type": w.media_type,
        "title": w.title,
        "poster_path": w.poster_path,
        "vote_average": w.vote_average,
        "overview": w.overview,
        "genre_ids": w.genre_ids,
        "release_date": w.release_date,
        "added_at": w.added_at.isoformat() if w.added_at else None,
        "rating": w.rating,
    }


@router.get("")
async def get_watched(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """La lista dell'utente corrente, dalla più recente."""
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id)
        .order_by(Watched.added_at.desc())
        .all()
    )
    return [_serialize(w) for w in rows]


@router.post("", status_code=201)
async def add_watched(
    item: WatchedItem,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Aggiunge un titolo alla lista dell'utente corrente."""
    db.add(Watched(user_id=user_id, **item.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Già nella lista")
    return {"ok": True}


@router.patch("/{tmdb_id}/{media_type}")
async def update_rating(
    tmdb_id: int,
    media_type: str,
    body: RatingUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Aggiorna il voto personale.

    Il filtro su user_id non è solo per correttezza: senza, chiunque potrebbe
    cambiare il voto nella lista di un altro conoscendone tmdb_id e media_type.
    Un titolo non proprio dà 404, non 403: non riveliamo cosa hanno gli altri.
    """
    updated = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == tmdb_id,
            Watched.media_type == media_type,
        )
        .update({"rating": body.rating})
    )
    db.commit()
    if updated == 0:
        raise HTTPException(404, "Non trovato")
    return {"ok": True}


@router.delete("/{tmdb_id}/{media_type}")
async def remove_watched(
    tmdb_id: int,
    media_type: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Rimuove un titolo dalla lista dell'utente corrente."""
    deleted = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == tmdb_id,
            Watched.media_type == media_type,
        )
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, "Non trovato nella lista")
    return {"ok": True}
