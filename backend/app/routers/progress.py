"""Progresso episodi delle serie TV (e anime). Ogni riga appartiene a un utente.

Segnare un episodio **tira dentro la serie** nella lista "Visti" (vedi
`services/watch_sync`): una puntata basta. Il contrario non vale — togliere tutti gli
episodi non rimuove la serie dai visti, perché lì possono esserci voto e recensione.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import EpisodeProgress
from ..schemas import EpisodeRef, SeasonMark
from ..services.watch_sync import ensure_series_watched

router = APIRouter(prefix="/api/progress", tags=["Episodes"])


@router.get("/{tmdb_id}")
async def get_progress(
    tmdb_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Episodi visti dall'utente per questa serie: solo le coordinate stagione/episodio."""
    rows = (
        db.query(EpisodeProgress.season_number, EpisodeProgress.episode_number)
        .filter(
            EpisodeProgress.user_id == user_id,
            EpisodeProgress.tmdb_id == tmdb_id,
        )
        .all()
    )
    return [
        {"season_number": s, "episode_number": e} for s, e in rows
    ]


@router.post("/{tmdb_id}/episode", status_code=201)
async def mark_episode(
    tmdb_id: int,
    ep: EpisodeRef,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Segna un singolo episodio come visto, e con esso la serie.

    Idempotente sull'episodio: se c'è già non lo riscrive. Il riallineamento della serie
    lo facciamo lo stesso, così anche le serie seguite *prima* di questa regola entrano
    nei visti al primo episodio segnato.
    """
    exists = (
        db.query(EpisodeProgress.id)
        .filter(
            EpisodeProgress.user_id == user_id,
            EpisodeProgress.tmdb_id == tmdb_id,
            EpisodeProgress.season_number == ep.season_number,
            EpisodeProgress.episode_number == ep.episode_number,
        )
        .first()
    )
    if not exists:
        db.add(
            EpisodeProgress(
                user_id=user_id,
                tmdb_id=tmdb_id,
                season_number=ep.season_number,
                episode_number=ep.episode_number,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            # Doppio click in parallelo: il vincolo UNIQUE regge, per noi è comunque "ok".
            db.rollback()

    return {"ok": True, "series": await ensure_series_watched(db, user_id, tmdb_id)}


@router.delete("/{tmdb_id}/episode/{season_number}/{episode_number}")
async def unmark_episode(
    tmdb_id: int,
    season_number: int,
    episode_number: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Toglie il "visto" da un singolo episodio."""
    db.query(EpisodeProgress).filter(
        EpisodeProgress.user_id == user_id,
        EpisodeProgress.tmdb_id == tmdb_id,
        EpisodeProgress.season_number == season_number,
        EpisodeProgress.episode_number == episode_number,
    ).delete()
    db.commit()
    return {"ok": True}


@router.post("/{tmdb_id}/season/{season_number}", status_code=201)
async def mark_season(
    tmdb_id: int,
    season_number: int,
    body: SeasonMark,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Segna in blocco gli episodi indicati di una stagione (solo quelli mancanti)."""
    already = {
        e
        for (e,) in db.query(EpisodeProgress.episode_number).filter(
            EpisodeProgress.user_id == user_id,
            EpisodeProgress.tmdb_id == tmdb_id,
            EpisodeProgress.season_number == season_number,
        )
    }
    to_add = [n for n in set(body.episode_numbers) if n not in already]
    if to_add:
        db.add_all(
            EpisodeProgress(
                user_id=user_id,
                tmdb_id=tmdb_id,
                season_number=season_number,
                episode_number=n,
            )
            for n in to_add
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    # `episode_numbers` non può essere vuoto (lo schema esige min_length=1): a questo
    # punto almeno un episodio della stagione risulta visto, quindi la serie pure.
    series = await ensure_series_watched(db, user_id, tmdb_id)
    return {"ok": True, "added": len(to_add), "series": series}


@router.delete("/{tmdb_id}/season/{season_number}")
async def unmark_season(
    tmdb_id: int,
    season_number: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Toglie il "visto" da tutti gli episodi di una stagione."""
    deleted = (
        db.query(EpisodeProgress)
        .filter(
            EpisodeProgress.user_id == user_id,
            EpisodeProgress.tmdb_id == tmdb_id,
            EpisodeProgress.season_number == season_number,
        )
        .delete()
    )
    db.commit()
    return {"ok": True, "removed": deleted}
