"""Schemi Pydantic (payload in ingresso/uscita delle API)."""

from pydantic import BaseModel, EmailStr, Field


# --- Watched ---

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
    rating: int = Field(..., ge=1, le=10)


# --- Auth ---

class RegisterRequest(BaseModel):
    """Passo 1: chiedo che mi arrivi il codice."""

    email: EmailStr


class RegisterComplete(BaseModel):
    """Passo 2: codice + credenziali scelte."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    # max_length=72: oltre, bcrypt tronca comunque — meglio dirlo subito all'utente
    # che accettare una password di cui conta solo l'inizio.
    password: str = Field(..., min_length=8, max_length=72)


class LoginRequest(BaseModel):
    # può contenere sia username sia email
    identifier: str
    password: str


# --- Progresso episodi ---

class EpisodeRef(BaseModel):
    """Riferimento a un singolo episodio di una serie."""

    season_number: int = Field(..., ge=0)
    episode_number: int = Field(..., ge=0)


class SeasonMark(BaseModel):
    """Segna in blocco un insieme di episodi di una stagione."""

    episode_numbers: list[int] = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
