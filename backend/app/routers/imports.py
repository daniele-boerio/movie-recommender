"""Import massivo da CSV (Letterboxd o generico).

Il frontend parsa il file e manda le righe a batch (già normalizzate: voto su scala 1-10).
Qui, per ogni riga, si cerca il titolo su TMDB, si prende il primo risultato e lo si
inserisce nei "Visti". L'esito torna riga per riga così il frontend aggiorna il progresso.
"""

import csv
import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models import Watched
from ..schemas import ImportRequest
from ..tmdb import tmdb_get

router = APIRouter(prefix="/api/import", tags=["Import"])


@router.post("/csv")
async def import_csv(
    payload: ImportRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    results = []
    for item in payload.items:
        title = (item.title or "").strip()
        if not title:
            results.append({"title": item.title, "status": "error"})
            continue

        media_type = "tv" if item.media_type == "tv" else "movie"

        # L'anno restringe i falsi positivi (film diversi con lo stesso titolo). Il nome
        # del parametro TMDB cambia tra film e serie.
        params = {"query": title, "page": 1}
        if item.year:
            params["first_air_date_year" if media_type == "tv" else "year"] = item.year

        try:
            data = await tmdb_get(f"/search/{media_type}", params)
        except Exception:
            results.append({"title": title, "status": "error"})
            continue

        hits = data.get("results") or []
        if not hits:
            results.append({"title": title, "status": "not_found"})
            continue

        top = hits[0]
        matched = top.get("title") or top.get("name") or title
        rating = None if item.rating is None else max(1, min(10, int(item.rating)))

        db.add(
            Watched(
                user_id=user_id,
                status="watched",
                tmdb_id=top["id"],
                media_type=media_type,
                title=matched,
                poster_path=top.get("poster_path"),
                vote_average=top.get("vote_average"),
                overview=top.get("overview"),
                genre_ids=json.dumps(top.get("genre_ids", [])),
                release_date=top.get("release_date") or top.get("first_air_date"),
                rating=rating,
            )
        )
        try:
            db.commit()
            results.append({"title": title, "status": "imported", "matched": matched})
        except IntegrityError:
            # Già in lista (o già in watchlist): il vincolo UNIQUE lo intercetta.
            db.rollback()
            results.append({"title": title, "status": "duplicate", "matched": matched})

    return {"results": results}


@router.get("/export")
async def export_csv(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Scarica tutta la libreria dell'utente come CSV.

    Colonne compatibili con l'importer (title/year/type/rating): il file esportato si
    può reimportare qui. `status` distingue visti da "da vedere"; `tmdb_id` è un extra.
    """
    rows = (
        db.query(Watched)
        .filter(Watched.user_id == user_id)
        .order_by(Watched.status, Watched.added_at.desc())
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["title", "year", "type", "rating", "status", "watched_on", "review", "tmdb_id"]
    )
    for w in rows:
        year = (w.release_date or "")[:4]
        writer.writerow(
            [
                w.title,
                year,
                w.media_type,
                "" if w.rating is None else w.rating,
                w.status,
                w.watched_on or "",
                w.review or "",
                w.tmdb_id,
            ]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=watchnext-export.csv"
        },
    )
