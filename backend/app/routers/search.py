"""Proxy TMDB: ricerca e scoperta. Nessun dato nostro, solo passacarte."""

from fastapi import APIRouter, Query

from ..services.smart_search import SearchFilters, search_titles, smart_search
from ..tmdb import tmdb_get

router = APIRouter(prefix="/api", tags=["Search"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    media_type: str = Query("multi", pattern="^(movie|tv|multi)$"),
    page: int = Query(1, ge=1),
    smart: bool = Query(True),
    genres: str | None = Query(None, description="id dei generi, separati da virgola (in OR)"),
    year_from: int | None = Query(None, ge=1900, le=2100),
    year_to: int | None = Query(None, ge=1900, le=2100),
    vote_min: float = Query(0, ge=0, le=10),
    original_language: str | None = Query(None, max_length=8),
    sort_by: str = Query("relevance"),
):
    """Cerca film / serie su TMDB.

    Di default la ricerca è "intelligente": riconosce anche attori, registi, case di
    produzione e temi (vedi `services/smart_search`). Con `smart=false` resta la sola
    ricerca per titolo.

    I filtri si applicano qui e non nel frontend: filtrare lato client la singola pagina
    la svuotava e spezzava l'ordinamento tra un "carica altri" e il successivo.
    """
    filters = SearchFilters.from_query(
        genres=genres,
        year_from=year_from,
        year_to=year_to,
        vote_min=vote_min,
        original_language=original_language,
        sort_by=sort_by,
    )

    if smart:
        return await smart_search(q, media_type, page, filters)

    results, total_pages = await search_titles(q, media_type, [page])
    return {
        "page": page,
        "results": filters.sorted_pool([r for r in results if filters.accepts(r)]),
        "total_pages": total_pages,
        "matched": {},
    }


@router.get("/trending")
async def trending(
    media_type: str = Query("all", pattern="^(movie|tv|all)$"),
    time_window: str = Query("week", pattern="^(day|week)$"),
    page: int = Query(1, ge=1),
):
    """Film / serie di tendenza."""
    data = await tmdb_get(f"/trending/{media_type}/{time_window}", {"page": page})
    data["results"] = [
        r for r in data.get("results", [])
        if r.get("media_type") in ("movie", "tv")
    ]
    return data


@router.get("/details/{media_type}/{tmdb_id}")
async def details(media_type: str, tmdb_id: int):
    """Dettaglio completo, con cast, simili, video e provider di streaming.

    `watch/providers` arriva con la chiave che contiene la barra (è il nome TMDB): il
    frontend legge `data['watch/providers'].results.IT` per la disponibilità in Italia.
    """
    data = await tmdb_get(
        f"/{media_type}/{tmdb_id}",
        {"append_to_response": "credits,similar,recommendations,videos,watch/providers"},
    )
    data["media_type"] = media_type
    return data


@router.get("/person/{person_id}")
async def person(person_id: int):
    """Scheda di una persona (attore/regista) con tutti i suoi film e serie."""
    return await tmdb_get(
        f"/person/{person_id}", {"append_to_response": "combined_credits"}
    )


@router.get("/tv/{tmdb_id}/season/{season_number}")
async def tv_season(tmdb_id: int, season_number: int):
    """Episodi di una stagione (per il tracking episodio-per-episodio)."""
    return await tmdb_get(f"/tv/{tmdb_id}/season/{season_number}")


@router.get("/genres/{media_type}")
async def genres(media_type: str):
    """Elenco generi (usato dai filtri)."""
    return await tmdb_get(f"/genre/{media_type}/list")


@router.get("/discover/{media_type}")
async def discover(
    media_type: str,
    with_genres: str | None = None,
    with_original_language: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    vote_min: float | None = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
):
    """Scopri film/serie per genere, anno, voto, lingua originale, ordinamento.

    La lingua originale serve per gli anime: TMDB non li classifica a parte, sono serie
    con genere Animazione (16) e `with_original_language=ja`.

    I nomi "puliti" (year_from/year_to/vote_min) li traduciamo qui nei parametri TMDB,
    che cambiano tra film (primary_release_date) e serie (first_air_date) e hanno il punto
    nel nome (non esprimibile come parametro Python).
    """
    params = {"sort_by": sort_by, "page": page}
    if with_genres:
        params["with_genres"] = with_genres
    if with_original_language:
        params["with_original_language"] = with_original_language

    if vote_min is not None:
        params["vote_average.gte"] = vote_min
        # Senza una soglia di voti, un titolo con 1 solo voto a 10 svetterebbe: lo evitiamo.
        params["vote_count.gte"] = 50

    date_field = "first_air_date" if media_type == "tv" else "primary_release_date"
    if year_from:
        params[f"{date_field}.gte"] = f"{year_from}-01-01"
    if year_to:
        params[f"{date_field}.lte"] = f"{year_to}-12-31"

    data = await tmdb_get(f"/discover/{media_type}", params)
    for r in data.get("results", []):
        r["media_type"] = media_type
    return data
