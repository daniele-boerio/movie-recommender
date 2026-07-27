"""Motore di raccomandazione: scoring dei candidati TMDB sui titoli visti."""

import json
from collections import Counter
from dataclasses import dataclass, field

from ..models import Watched
from ..tmdb import tmdb_get

ANIMATION_GENRE = 16


@dataclass(frozen=True)
class RecFilters:
    """Cosa l'utente non vuole vedere tra i consigli.

    Si applicano *prima* della classifica, non dopo: filtrare i primi N ranked lascerebbe
    la pagina vuota proprio nel caso che conta (tutti i primi 40 sono cartoni animati).
    """

    media_type: str = "all"                          # all | movie | tv
    exclude_genres: frozenset[int] = field(default_factory=frozenset)
    exclude_anime: bool = False                      # animazione giapponese
    min_vote: float = 0.0
    year_from: int | None = None
    year_to: int | None = None

    @property
    def active(self) -> bool:
        return bool(
            self.media_type != "all"
            or self.exclude_genres
            or self.exclude_anime
            or self.min_vote
            or self.year_from
            or self.year_to
        )

    def accepts(self, item: dict, media_type: str) -> bool:
        if self.media_type != "all" and media_type != self.media_type:
            return False

        genres = set(item.get("genre_ids") or [])
        if genres & self.exclude_genres:
            return False
        if (
            self.exclude_anime
            and ANIMATION_GENRE in genres
            and item.get("original_language") == "ja"
        ):
            return False

        if self.min_vote and (item.get("vote_average") or 0) < self.min_vote:
            return False

        if self.year_from or self.year_to:
            date = item.get("release_date") or item.get("first_air_date") or ""
            year = int(date[:4]) if date[:4].isdigit() else None
            if year is None:
                return False  # senza data non possiamo dire che rispetti il range
            if self.year_from and year < self.year_from:
                return False
            if self.year_to and year > self.year_to:
                return False

        return True


async def build_recommendations(
    watched_rows: list[Watched],
    limit: int,
    exclude: set[tuple] | None = None,
    filters: RecFilters | None = None,
) -> dict:
    """
    1. Per ogni titolo visto, chiede a TMDB "recommendations" e "similar"
    2. Scarta i candidati esclusi dai filtri dell'utente
    3. Assegna a ogni candidato uno score dato da:
       - quanti titoli visti lo consigliano (frequenza)
       - affinità coi generi preferiti dell'utente
       - voto medio TMDB
       - voto personale del titolo che l'ha generato
    4. Esclude quelli già in lista (`exclude`: visti + watchlist; default = i soli visti)
    5. Restituisce i primi N
    """
    if not watched_rows:
        return {
            "results": [],
            "message": "Aggiungi film/serie alla tua lista per ricevere consigli!",
        }

    filters = filters or RecFilters()
    watched_set = (
        exclude if exclude is not None else {(r.tmdb_id, r.media_type) for r in watched_rows}
    )

    # Profilo dei generi, pesato sul voto personale.
    genre_counter: Counter = Counter()
    for r in watched_rows:
        if r.genre_ids:
            try:
                for g in json.loads(r.genre_ids):
                    genre_counter[g] += r.rating if r.rating else 5
            except (json.JSONDecodeError, TypeError):
                pass

    # Normalizzato 0–1 sul genere preferito: la somma grezza cresce con la lista e finisce
    # per schiacciare gli altri segnali (con 30 titoli Marvel visti, qualunque cosa fosse
    # azione+avventura vinceva — cartoni animati compresi).
    top_genre = max(genre_counter.values(), default=0) or 1
    genre_profile = {g: v / top_genre for g, v in genre_counter.items()}

    candidates: dict[tuple, dict] = {}
    seed_rating: dict[tuple, int] = {}  # miglior voto personale tra i titoli che l'hanno suggerito
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
                if not filters.accepts(item, item_mt):
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
                        "original_language": item.get("original_language"),
                        "release_date": item.get("release_date") or item.get("first_air_date", ""),
                        "score": 0,
                        "frequency": 0,
                        "recommended_by": [],
                    }

                c = candidates[key]
                c["frequency"] += 1
                c["recommended_by"].append(row.title)
                seed_rating[key] = max(seed_rating.get(key, 0), personal_rating)

                # I generi del candidato: la *media* dell'affinità, non la somma, altrimenti
                # basta essere etichettati con mezzo catalogo per vincere.
                genres = item.get("genre_ids") or []
                affinity = (
                    sum(genre_profile.get(g, 0) for g in genres) / len(genres) if genres else 0
                )

                freq_score = c["frequency"] * 10
                tmdb_score = (item.get("vote_average", 0) or 0) * 2
                personal_boost = seed_rating[key] * 1.5
                c["score"] = round(freq_score + tmdb_score + personal_boost + affinity * 15, 2)

    ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)

    # "Perché hai visto X": massimo 3, senza duplicati
    for item in ranked:
        item["recommended_by"] = list(dict.fromkeys(item["recommended_by"]))[:3]

    return {"results": ranked[:limit], "filtered": filters.active}
