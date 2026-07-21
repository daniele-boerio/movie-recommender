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
from ..models import CustomList, ListItem, ListMember, Notification, User
from ..schemas import ListCreate, ListItemAdd, ListRename, MemberAdd

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
    """Solo il proprietario: rinomina, elimina, gestione membri."""
    lst = (
        db.query(CustomList)
        .filter(CustomList.id == list_id, CustomList.user_id == user_id)
        .first()
    )
    if not lst:
        raise HTTPException(404, "Lista non trovata")
    return lst


def _accessible_list(db: Session, user_id: int, list_id: int) -> CustomList:
    """Proprietario o membro: leggere la lista e aggiungere/togliere titoli."""
    lst = db.query(CustomList).filter(CustomList.id == list_id).first()
    if lst and (
        lst.user_id == user_id
        or db.query(ListMember)
        .filter(ListMember.list_id == list_id, ListMember.user_id == user_id)
        .first()
    ):
        return lst
    raise HTTPException(404, "Lista non trovata")


@router.get("")
def get_lists(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Le liste dell'utente (possedute + quelle di cui è membro), con anteprima."""
    owned = db.query(CustomList).filter(CustomList.user_id == user_id).all()
    member_of = (
        db.query(CustomList)
        .join(ListMember, ListMember.list_id == CustomList.id)
        .filter(ListMember.user_id == user_id)
        .all()
    )
    # id decrescente = dalle più recenti; l'id è monotono con la creazione.
    all_lists = sorted(owned + member_of, key=lambda lst: lst.id, reverse=True)

    out = []
    for lst in all_lists:
        items = (
            db.query(ListItem)
            .filter(ListItem.list_id == lst.id)
            .order_by(ListItem.added_at.desc())
            .all()
        )
        member_count = (
            db.query(ListMember).filter(ListMember.list_id == lst.id).count()
        )
        out.append(
            {
                "id": lst.id,
                "name": lst.name,
                "count": len(items),
                "preview": [i.poster_path for i in items[:4] if i.poster_path],
                "is_owner": lst.user_id == user_id,
                "shared": member_count > 0,
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
    lst = _accessible_list(db, user_id, list_id)
    items = (
        db.query(ListItem)
        .filter(ListItem.list_id == lst.id)
        .order_by(ListItem.added_at.desc())
        .all()
    )
    members = (
        db.query(User)
        .join(ListMember, ListMember.user_id == User.id)
        .filter(ListMember.list_id == lst.id)
        .order_by(User.username)
        .all()
    )
    owner = db.get(User, lst.user_id)
    return {
        "id": lst.id,
        "name": lst.name,
        "is_owner": lst.user_id == user_id,
        "owner": owner.username if owner else None,
        "members": [{"id": m.id, "username": m.username} for m in members],
        "items": [_serialize_item(i) for i in items],
    }


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
    lst = _accessible_list(db, user_id, list_id)  # proprietario o membro
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

    # Se la lista è condivisa, avvisa gli altri partecipanti (non chi ha appena aggiunto).
    member_ids = [
        m[0] for m in db.query(ListMember.user_id).filter(ListMember.list_id == list_id).all()
    ]
    if member_ids:
        recipients = (set(member_ids) | {lst.user_id}) - {user_id}
        if recipients:
            actor = db.get(User, user_id)
            ref = f"listitem:{list_id}:{body.tmdb_id}:{media_type}"
            for rid in recipients:
                db.add(
                    Notification(
                        user_id=rid,
                        type="list_item",
                        tmdb_id=body.tmdb_id,
                        media_type=media_type,
                        title=body.title,
                        body=f"{actor.username} ha aggiunto «{body.title}» alla lista «{lst.name}»",
                        ref=ref,
                        poster_path=body.poster_path,
                    )
                )
            db.commit()

    return {"ok": True}


@router.delete("/{list_id}/items/{tmdb_id}/{media_type}")
def remove_item(
    list_id: int,
    tmdb_id: int,
    media_type: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _accessible_list(db, user_id, list_id)  # proprietario o membro
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


@router.post("/{list_id}/members", status_code=201)
def add_member(
    list_id: int,
    body: MemberAdd,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Invita un utente nella lista (solo il proprietario)."""
    lst = _owned_list(db, user_id, list_id)
    u = db.query(User).filter(User.username == body.username.lower()).first()
    if not u:
        raise HTTPException(404, "Utente non trovato")
    if u.id == lst.user_id:
        raise HTTPException(400, "Il proprietario fa già parte della lista")
    db.add(ListMember(list_id=list_id, user_id=u.id))
    try:
        db.commit()
        newly_added = True
    except IntegrityError:
        db.rollback()  # già membro: idempotente
        newly_added = False

    if newly_added:
        actor = db.get(User, user_id)
        db.add(
            Notification(
                user_id=u.id,
                type="list_invite",
                title=lst.name,
                body=f"{actor.username} ti ha aggiunto alla lista «{lst.name}»",
            )
        )
        db.commit()
    return {"ok": True}


@router.delete("/{list_id}/members/{member_id}")
def remove_member(
    list_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Rimuove un membro. Il proprietario può togliere chiunque; un membro può togliere
    solo se stesso (lasciare la lista)."""
    lst = db.query(CustomList).filter(CustomList.id == list_id).first()
    if not lst:
        raise HTTPException(404, "Lista non trovata")
    if lst.user_id != user_id and member_id != user_id:
        # Non sei il proprietario e non stai lasciando: non riveliamo nemmeno l'esistenza.
        raise HTTPException(404, "Lista non trovata")
    db.query(ListMember).filter(
        ListMember.list_id == list_id, ListMember.user_id == member_id
    ).delete()
    db.commit()
    return {"ok": True}
