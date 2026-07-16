"""Schemi Pydantic (payload in ingresso/uscita delle API)."""

from pydantic import BaseModel


class WatchedItem(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" | "tv"
    title: str
    poster_path: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: str | None = None  # stringa JSON "[28,12,...]"
    release_date: str | None = None
    rating: int | None = None  # voto personale 1-10


class RatingUpdate(BaseModel):
    rating: int  # 1-10
