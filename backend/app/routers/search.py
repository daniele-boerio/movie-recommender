"""Proxy TMDB: ricerca e scoperta. Nessun dato nostro, solo passacarte."""

from fastapi import APIRouter, Query

from ..tmdb import tmdb_get

router = APIRouter(prefix="/api", tags=["Search"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    media_type: str = Query("multi", pattern="^(movie|tv|multi)$"),
    page: int = Query(1, ge=1),
):
    """Cerca film / serie su TMDB."""
    if media_type == "multi":
        data = await tmdb_get("/search/multi", {"query": q, "page": page})
        # /search/multi restituisce anche le persone: le scartiamo
        data["results"] = [
            r for r in data.get("results", [])
            if r.get("media_type") in ("movie", "tv")
        ]
    else:
        data = await tmdb_get(f"/search/{media_type}", {"query": q, "page": page})
        for r in data.get("results", []):
            r["media_type"] = media_type
    return data


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
    """Dettaglio completo, con cast e simili."""
    data = await tmdb_get(
        f"/{media_type}/{tmdb_id}",
        {"append_to_response": "credits,similar,recommendations,videos"},
    )
    data["media_type"] = media_type
    return data


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
    sort_by: str = "popularity.desc",
    page: int = 1,
):
    """Scopri film/serie per genere, lingua originale, ordinamento, ecc.

    La lingua originale serve per gli anime: TMDB non li classifica a parte, sono serie
    con genere Animazione (16) e `with_original_language=ja`.
    """
    params = {"sort_by": sort_by, "page": page}
    if with_genres:
        params["with_genres"] = with_genres
    if with_original_language:
        params["with_original_language"] = with_original_language
    data = await tmdb_get(f"/discover/{media_type}", params)
    for r in data.get("results", []):
        r["media_type"] = media_type
    return data
