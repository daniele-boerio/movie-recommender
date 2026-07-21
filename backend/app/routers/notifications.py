"""Centro notifiche in-app: elenco, conteggio non lette, segna come lette."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": n.id,
            "type": n.type,
            "tmdb_id": n.tmdb_id,
            "media_type": n.media_type,
            "title": n.title,
            "body": n.body,
            "poster_path": n.poster_path,
            "read": n.read_at is not None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
        .count()
    )
    return {"count": count}


@router.post("/read")
def mark_all_read(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Segna come lette tutte le notifiche dell'utente."""
    db.query(Notification).filter(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    ).update({"read_at": datetime.now(timezone.utc)})
    db.commit()
    return {"ok": True}
