"""CRUD della lista "Visti"."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Watched
from ..schemas import RatingUpdate, WatchedItem

router = APIRouter(prefix="/api/watched", tags=["Watched"])


def _serialize(w: Watched) -> dict:
    """Il frontend si aspetta le stesse chiavi che restituiva sqlite3."""
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
async def get_watched(db: Session = Depends(get_db)):
    """Tutta la lista, dal più recente."""
    rows = db.query(Watched).order_by(Watched.added_at.desc()).all()
    return [_serialize(w) for w in rows]


@router.post("", status_code=201)
async def add_watched(item: WatchedItem, db: Session = Depends(get_db)):
    """Aggiunge un titolo alla lista."""
    db.add(Watched(**item.model_dump()))
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
):
    """Aggiorna il voto personale."""
    updated = (
        db.query(Watched)
        .filter(Watched.tmdb_id == tmdb_id, Watched.media_type == media_type)
        .update({"rating": body.rating})
    )
    db.commit()
    if updated == 0:
        raise HTTPException(404, "Non trovato")
    return {"ok": True}


@router.delete("/{tmdb_id}/{media_type}")
async def remove_watched(tmdb_id: int, media_type: str, db: Session = Depends(get_db)):
    """Rimuove un titolo dalla lista."""
    deleted = (
        db.query(Watched)
        .filter(Watched.tmdb_id == tmdb_id, Watched.media_type == media_type)
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, "Non trovato nella lista")
    return {"ok": True}
