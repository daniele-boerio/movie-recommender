"""Social: ricerca utenti, profili pubblici, follow.

Un profilo pubblico mostra solo i titoli VISTI con i relativi voti: watchlist e liste
restano private. I dati altrui sono di sola lettura per definizione (nessun endpoint qui
modifica righe di un altro utente).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Follow, User, Watched

router = APIRouter(prefix="/api", tags=["Social"])


def _user_or_404(db: Session, username: str) -> User:
    u = db.query(User).filter(User.username == username.lower()).first()
    if not u:
        raise HTTPException(404, "Utente non trovato")
    return u


@router.get("/users/search")
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Cerca utenti per prefisso di username (niente directory sfogliabile)."""
    term = q.strip().lower()
    if len(term) < 2:
        return []
    rows = (
        db.query(User)
        .filter(User.username.ilike(f"{term}%"), User.id != user_id)
        .order_by(User.username)
        .limit(10)
        .all()
    )
    following = {
        f.following_id
        for f in db.query(Follow.following_id).filter(Follow.follower_id == user_id).all()
    }
    return [
        {"id": u.id, "username": u.username, "is_following": u.id in following}
        for u in rows
    ]


@router.get("/users/{username}")
def get_profile(
    username: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    u = _user_or_404(db, username)

    watched = (
        db.query(Watched)
        .filter(Watched.user_id == u.id, Watched.status == "watched")
        .order_by(Watched.added_at.desc())
        .all()
    )
    movie = sum(1 for w in watched if w.media_type == "movie")
    tv = sum(1 for w in watched if w.media_type == "tv")
    ratings = [w.rating for w in watched if w.rating]
    avg = round(sum(ratings) / len(ratings), 1) if ratings else None

    is_following = (
        db.query(Follow)
        .filter(Follow.follower_id == user_id, Follow.following_id == u.id)
        .first()
        is not None
    )
    followers = db.query(Follow).filter(Follow.following_id == u.id).count()
    following = db.query(Follow).filter(Follow.follower_id == u.id).count()

    # Solo poster/titolo/voto personale: niente recensioni (restano nel diario privato).
    items = [
        {
            "tmdb_id": w.tmdb_id,
            "media_type": w.media_type,
            "title": w.title,
            "poster_path": w.poster_path,
            "vote_average": w.vote_average,
            "release_date": w.release_date,
            "rating": w.rating,
        }
        for w in watched[:60]
    ]

    return {
        "id": u.id,
        "username": u.username,
        "is_self": u.id == user_id,
        "is_following": is_following,
        "followers": followers,
        "following": following,
        "stats": {"movie": movie, "tv": tv, "all": movie + tv, "avg_rating": avg},
        "watched": items,
    }


@router.post("/users/{username}/follow", status_code=201)
def follow_user(
    username: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    u = _user_or_404(db, username)
    if u.id == user_id:
        raise HTTPException(400, "Non puoi seguire te stesso")
    db.add(Follow(follower_id=user_id, following_id=u.id))
    try:
        db.commit()
    except IntegrityError:
        # Già seguito: l'operazione è idempotente, non è un errore.
        db.rollback()
    return {"ok": True}


@router.delete("/users/{username}/follow")
def unfollow_user(
    username: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    u = _user_or_404(db, username)
    db.query(Follow).filter(
        Follow.follower_id == user_id, Follow.following_id == u.id
    ).delete()
    db.commit()
    return {"ok": True}


@router.get("/social/following")
def my_following(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Gli utenti che seguo."""
    rows = (
        db.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == user_id)
        .order_by(User.username)
        .all()
    )
    return [{"id": u.id, "username": u.username} for u in rows]
