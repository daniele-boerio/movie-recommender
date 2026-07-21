"""CRUD della lista "Visti". Ogni riga appartiene a un utente.

`watched` è condivisa con la watchlist "Da vedere" (vedi routers/watchlist.py): le due
liste sono la stessa tabella distinta dalla colonna `status`. Qui si lavora solo sulle
righe `status == 'watched'`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..schemas import WatchedItem, WatchedPatch

router = APIRouter(prefix="/api/watched", tags=["Watched"])


def _serialize(w: Watched) -> dict:
    """Il frontend si aspetta le stesse chiavi di prima. user_id non esce: è un
    dettaglio interno, il client vede solo la propria roba per definizione."""
    return {
        "id": w.id,
        "tmdb_id": w.tmdb_id,
        "media_type": w.media_type,
        "status": w.status,
        "title": w.title,
        "poster_path": w.poster_path,
        "vote_average": w.vote_average,
        "overview": w.overview,
        "genre_ids": w.genre_ids,
        "release_date": w.release_date,
        "added_at": w.added_at.isoformat() if w.added_at else None,
        "rating": w.rating,
        "review": w.review,
        "watched_on": w.watched_on,
    }


@router.get("")
async def get_watched(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """La lista "Visti" dell'utente corrente, dalla più recente."""
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id, Watched.status == "watched")
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
    """Segna un titolo come visto.

    Se era nella watchlist "Da vedere", lo sposta invece di duplicarlo: il vincolo
    UNIQUE(user_id, tmdb_id, media_type) vieta comunque due righe per lo stesso titolo.
    """
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
        if existing.status == "watchlist":
            existing.status = "watched"
            existing.added_at = datetime.now(timezone.utc)  # risale la lista dei visti
            db.commit()
            return {"ok": True, "moved": True}
        raise HTTPException(409, "Già nella lista")

    db.add(Watched(user_id=user_id, status="watched", **item.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        # Race con un'altra richiesta in parallelo: il vincolo UNIQUE è l'arbitro finale.
        db.rollback()
        raise HTTPException(409, "Già nella lista")
    return {"ok": True}


@router.patch("/{tmdb_id}/{media_type}")
async def update_watched(
    tmdb_id: int,
    media_type: str,
    body: WatchedPatch,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Aggiorna voto, recensione e/o data di visione di un titolo visto.

    Si toccano solo i campi presenti nel payload (model_fields_set), così aggiornare
    il voto non azzera la recensione e viceversa.

    Il filtro su user_id non è solo per correttezza: senza, chiunque potrebbe modificare
    la riga di un altro conoscendone tmdb_id e media_type. Un titolo non proprio dà 404,
    non 403: non riveliamo cosa hanno gli altri.
    """
    values = {
        field: getattr(body, field)
        for field in body.model_fields_set
        if field in ("rating", "review", "watched_on")
    }
    if not values:
        raise HTTPException(400, "Nessun campo da aggiornare")

    updated = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == tmdb_id,
            Watched.media_type == media_type,
            Watched.status == "watched",  # diario e voto hanno senso solo su un titolo visto
        )
        .update(values)
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
    """Rimuove un titolo dalla lista "Visti" dell'utente corrente."""
    deleted = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == tmdb_id,
            Watched.media_type == media_type,
            Watched.status == "watched",
        )
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, "Non trovato nella lista")
    return {"ok": True}
