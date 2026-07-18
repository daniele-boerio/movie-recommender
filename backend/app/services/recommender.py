"""Motore di raccomandazione: scoring dei candidati TMDB sui titoli visti."""

import json
from collections import Counter

from ..models import Watched
from ..tmdb import tmdb_get


async def build_recommendations(
    watched_rows: list[Watched],
    limit: int,
    exclude: set[tuple] | None = None,
) -> dict:
    """
    1. Per ogni titolo visto, chiede a TMDB "recommendations" e "similar"
    2. Assegna a ogni candidato uno score dato da:
       - quanti titoli visti lo consigliano (frequenza)
       - sovrapposizione coi generi preferiti dell'utente
       - voto medio TMDB
       - voto personale del titolo che l'ha generato
    3. Esclude quelli già in lista (`exclude`: visti + watchlist; default = i soli visti)
    4. Restituisce i primi N
    """
    if not watched_rows:
        return {
            "results": [],
            "message": "Aggiungi film/serie alla tua lista per ricevere consigli!",
        }

    watched_set = (
        exclude if exclude is not None else {(r.tmdb_id, r.media_type) for r in watched_rows}
    )

    # Profilo dei generi, pesato sul voto personale
    genre_counter: Counter = Counter()
    for r in watched_rows:
        if r.genre_ids:
            try:
                for g in json.loads(r.genre_ids):
                    genre_counter[g] += r.rating if r.rating else 5
            except (json.JSONDecodeError, TypeError):
                pass

    candidates: dict[tuple, dict] = {}
    sample = watched_rows[:30]  # tetto alle chiamate TMDB

    for row in sample:
        mt = row.media_type
        tid = row.tmdb_id
        personal_rating = row.rating or 5

        for endpoint in ("recommendations", "similar"):
            try:
                data = await tmdb_get(f"/{mt}/{tid}/{endpoint}", {"page": 1})
            except Exception:
                continue

            for item in data.get("results", [])[:10]:
                item_mt = item.get("media_type", mt)
                item_id = item.get("id")
                key = (item_id, item_mt)

                if key in watched_set:
                    continue

                if key not in candidates:
                    candidates[key] = {
                        "tmdb_id": item_id,
                        "media_type": item_mt,
                        "title": item.get("title") or item.get("name", ""),
                        "poster_path": item.get("poster_path"),
                        "vote_average": item.get("vote_average", 0),
                        "overview": item.get("overview", ""),
                        "genre_ids": item.get("genre_ids", []),
                        "release_date": item.get("release_date") or item.get("first_air_date", ""),
                        "score": 0,
                        "frequency": 0,
                        "recommended_by": [],
                    }

                c = candidates[key]
                c["frequency"] += 1
                c["recommended_by"].append(row.title)

                freq_score = c["frequency"] * 10
                tmdb_score = (item.get("vote_average", 0) or 0) * 2
                personal_boost = personal_rating * 1.5
                genre_overlap = sum(
                    genre_counter.get(g, 0) for g in item.get("genre_ids", [])
                )
                c["score"] = freq_score + tmdb_score + personal_boost + genre_overlap

    ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)

    # "Perché hai visto X": massimo 3, senza duplicati
    for item in ranked:
        item["recommended_by"] = list(dict.fromkeys(item["recommended_by"]))[:3]

    return {"results": ranked[:limit]}
