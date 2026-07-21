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

    # Compatibilità di gusti: sui titoli che entrambi abbiamo visto E votato, quanto
    # sono vicini i voti. Differenza media su scala 1-10 (max 9) → percentuale di affinità.
    compatibility = None
    if u.id != user_id:
        their_rated = {
            (w.tmdb_id, w.media_type): w.rating for w in watched if w.rating is not None
        }
        my_rated = {
            (w.tmdb_id, w.media_type): w.rating
            for w in db.query(Watched).filter(
                Watched.user_id == user_id,
                Watched.status == "watched",
                Watched.rating.isnot(None),
            ).all()
        }
        common = set(their_rated) & set(my_rated)
        score = None
        if common:
            avg_diff = sum(abs(their_rated[k] - my_rated[k]) for k in common) / len(common)
            score = round(100 * (1 - avg_diff / 9))
        compatibility = {"score": score, "common": len(common)}

    return {
        "id": u.id,
        "username": u.username,
        "is_self": u.id == user_id,
        "is_following": is_following,
        "followers": followers,
        "following": following,
        "stats": {"movie": movie, "tv": tv, "all": movie + tv, "avg_rating": avg},
        "compatibility": compatibility,
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


def _mutual_ids(db: Session, user_id: int, other_ids: set[int]) -> set[int]:
    """Fra `other_ids`, quali seguono a loro volta `user_id` (follow reciproco)."""
    if not other_ids:
        return set()
    return {
        f.follower_id
        for f in db.query(Follow.follower_id)
        .filter(Follow.following_id == user_id, Follow.follower_id.in_(other_ids))
        .all()
    }


@router.get("/social/following")
def my_following(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Gli utenti che seguo (con flag `mutual` se mi seguono a loro volta)."""
    rows = (
        db.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == user_id)
        .order_by(User.username)
        .all()
    )
    mutual = _mutual_ids(db, user_id, {u.id for u in rows})
    return [
        {"id": u.id, "username": u.username, "mutual": u.id in mutual} for u in rows
    ]


@router.get("/social/followers")
def my_followers(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Gli utenti che mi seguono. `following` = se li seguo anch'io (reciproco)."""
    rows = (
        db.query(User)
        .join(Follow, Follow.follower_id == User.id)
        .filter(Follow.following_id == user_id)
        .order_by(User.username)
        .all()
    )
    # Chi seguo io, per marcare i reciproci.
    i_follow = {
        f.following_id
        for f in db.query(Follow.following_id).filter(Follow.follower_id == user_id).all()
    }
    return [
        {"id": u.id, "username": u.username, "following": u.id in i_follow}
        for u in rows
    ]


@router.get("/social/feed")
def feed(
    limit: int = Query(40, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Attività recente di chi seguo: i loro ultimi titoli segnati come visti."""
    rows = (
        db.query(Watched, User.username)
        .join(Follow, Follow.following_id == Watched.user_id)
        .join(User, User.id == Watched.user_id)
        .filter(Follow.follower_id == user_id, Watched.status == "watched")
        .order_by(Watched.added_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "username": uname,
            "tmdb_id": w.tmdb_id,
            "media_type": w.media_type,
            "title": w.title,
            "poster_path": w.poster_path,
            "vote_average": w.vote_average,
            "release_date": w.release_date,
            "rating": w.rating,
            "added_at": w.added_at.isoformat() if w.added_at else None,
        }
        for w, uname in rows
    ]
