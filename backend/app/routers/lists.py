"""Liste personalizzate dell'utente ("Film di Natale", "Da vedere con lei", …).

Ogni lista e ogni suo elemento appartengono all'utente: le operazioni sui titoli passano
sempre da _owned_list, che dà 404 (non 403) su una lista non propria — non riveliamo
l'esistenza delle liste altrui.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import CustomList, ListItem
from ..schemas import ListCreate, ListItemAdd, ListRename

router = APIRouter(prefix="/api/lists", tags=["Lists"])


def _serialize_item(i: ListItem) -> dict:
    return {
        "tmdb_id": i.tmdb_id,
        "media_type": i.media_type,
        "title": i.title,
        "poster_path": i.poster_path,
        "vote_average": i.vote_average,
        "release_date": i.release_date,
    }


def _owned_list(db: Session, user_id: int, list_id: int) -> CustomList:
    lst = (
        db.query(CustomList)
        .filter(CustomList.id == list_id, CustomList.user_id == user_id)
        .first()
    )
    if not lst:
        raise HTTPException(404, "Lista non trovata")
    return lst


@router.get("")
def get_lists(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Le liste dell'utente, con conteggio e qualche poster per l'anteprima."""
    lists = (
        db.query(CustomList)
        .filter(CustomList.user_id == user_id)
        .order_by(CustomList.created_at.desc())
        .all()
    )
    out = []
    for lst in lists:
        items = (
            db.query(ListItem)
            .filter(ListItem.list_id == lst.id)
            .order_by(ListItem.added_at.desc())
            .all()
        )
        out.append(
            {
                "id": lst.id,
                "name": lst.name,
                "count": len(items),
                "preview": [i.poster_path for i in items[:4] if i.poster_path],
            }
        )
    return out


@router.post("", status_code=201)
def create_list(
    body: ListCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    lst = CustomList(user_id=user_id, name=body.name.strip())
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return {"id": lst.id, "name": lst.name, "count": 0, "preview": []}


@router.get("/{list_id}")
def get_list(
    list_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    lst = _owned_list(db, user_id, list_id)
    items = (
        db.query(ListItem)
        .filter(ListItem.list_id == lst.id)
        .order_by(ListItem.added_at.desc())
        .all()
    )
    return {"id": lst.id, "name": lst.name, "items": [_serialize_item(i) for i in items]}


@router.patch("/{list_id}")
def rename_list(
    list_id: int,
    body: ListRename,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    lst = _owned_list(db, user_id, list_id)
    lst.name = body.name.strip()
    db.commit()
    return {"ok": True}


@router.delete("/{list_id}")
def delete_list(
    list_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    lst = _owned_list(db, user_id, list_id)
    db.delete(lst)  # gli elementi spariscono per cascata (FK ondelete=CASCADE)
    db.commit()
    return {"ok": True}


@router.post("/{list_id}/items", status_code=201)
def add_item(
    list_id: int,
    body: ListItemAdd,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _owned_list(db, user_id, list_id)
    media_type = "tv" if body.media_type == "tv" else "movie"
    db.add(
        ListItem(
            list_id=list_id,
            tmdb_id=body.tmdb_id,
            media_type=media_type,
            title=body.title,
            poster_path=body.poster_path,
            vote_average=body.vote_average,
            release_date=body.release_date,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Già nella lista")
    return {"ok": True}


@router.delete("/{list_id}/items/{tmdb_id}/{media_type}")
def remove_item(
    list_id: int,
    tmdb_id: int,
    media_type: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _owned_list(db, user_id, list_id)
    deleted = (
        db.query(ListItem)
        .filter(
            ListItem.list_id == list_id,
            ListItem.tmdb_id == tmdb_id,
            ListItem.media_type == media_type,
        )
        .delete()
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(404, "Non trovato nella lista")
    return {"ok": True}
