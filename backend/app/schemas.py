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


class WatchedPatch(BaseModel):
    """Aggiornamento parziale di un titolo visto: voto, recensione, data di visione.

    Tutti opzionali; si aggiornano solo i campi effettivamente presenti nel payload
    (lo distingue `model_fields_set`), così mandare solo il voto non cancella la recensione.
    """

    rating: int | None = Field(None, ge=1, le=10)
    review: str | None = None
    watched_on: str | None = None


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


class ChangePasswordRequest(BaseModel):
    current_password: str
    # stessi vincoli della registrazione: oltre i 72 byte bcrypt tronca comunque.
    new_password: str = Field(..., min_length=8, max_length=72)


class ChangeEmailRequest(BaseModel):
    """Passo 1: chiedo il codice sul nuovo indirizzo, confermando con la password."""

    new_email: EmailStr
    password: str


class ChangeEmailConfirm(BaseModel):
    """Passo 2: il codice ricevuto sul nuovo indirizzo."""

    new_email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class DeleteAccountRequest(BaseModel):
    password: str


class PasswordResetRequest(BaseModel):
    """Passo 1: chiedo un codice per reimpostare la password dimenticata."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Passo 2: codice ricevuto via email + nuova password."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=72)


# --- Progresso episodi ---

class EpisodeRef(BaseModel):
    """Riferimento a un singolo episodio di una serie."""

    season_number: int = Field(..., ge=0)
    episode_number: int = Field(..., ge=0)


class SeasonMark(BaseModel):
    """Segna in blocco un insieme di episodi di una stagione."""

    episode_numbers: list[int] = Field(..., min_length=1)


# --- Import CSV ---

class ImportItem(BaseModel):
    """Una riga di CSV già normalizzata dal frontend. Il voto arriva già su scala 1-10."""

    title: str
    year: int | None = None
    media_type: str = "movie"  # "movie" | "tv"
    rating: int | None = None


class ImportRequest(BaseModel):
    """Un batch di righe da importare. Il frontend spezza il file per mostrare il progresso."""

    items: list[ImportItem] = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
