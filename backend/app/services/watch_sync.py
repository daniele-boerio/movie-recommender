"""Regola: una puntata vista basta a considerare vista la serie.

Chi segna anche un solo episodio la serie l'ha iniziata: lasciarla fuori dai "Visti"
(o peggio, lasciarla in "Da vedere") obbligava a segnarla di nuovo a mano. Sta qui e
non nel frontend perché è una regola sui dati: deve valere per chiunque chiami l'API.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Watched
from ..tmdb import tmdb_get


async def ensure_series_watched(db: Session, user_id: int, tmdb_id: int) -> str:
    """Porta la serie tra i "Visti" dell'utente. Torna cosa è successo:

    - `already`  c'era già: non si tocca niente (voto, recensione e data restano)
    - `moved`    era in "Da vedere": spostata
    - `added`    non c'era: creata coi dati TMDB
    - `skipped`  TMDB non risponde: senza titolo non possiamo creare la riga
    """
    row = (
        db.query(Watched)
        .filter(
            Watched.user_id == user_id,
            Watched.tmdb_id == tmdb_id,
            Watched.media_type == "tv",
        )
        .first()
    )
    if row:
        if row.status == "watched":
            return "already"
        row.status = "watched"
        row.added_at = datetime.now(timezone.utc)  # risale la lista dei visti
        db.commit()
        return "moved"

    try:
        data = await tmdb_get(f"/tv/{tmdb_id}")
    except Exception:
        # Meglio nessuna riga che una riga senza titolo: il progresso resta salvato
        # comunque, e il prossimo episodio segnato riproverà.
        return "skipped"

    db.add(
        Watched(
            user_id=user_id,
            status="watched",
            tmdb_id=tmdb_id,
            media_type="tv",
            title=data.get("name") or data.get("original_name") or f"Serie {tmdb_id}",
            poster_path=data.get("poster_path"),
            vote_average=data.get("vote_average"),
            overview=data.get("overview"),
            # Il dettaglio TMDB dà `genres: [{id, name}]`, non `genre_ids` come le liste.
            genre_ids=json.dumps([g["id"] for g in data.get("genres") or [] if "id" in g]),
            release_date=data.get("first_air_date"),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # corsa con un'altra richiesta: l'ha già creata lei
        return "already"
    return "added"
