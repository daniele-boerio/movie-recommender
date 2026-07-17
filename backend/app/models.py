"""Modelli SQLAlchemy."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    # email e username sono sempre salvati in minuscolo (normalizzati nel router)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    # Incrementandola si invalidano di colpo tutti gli access token già emessi
    # (es. al cambio password), senza dover aspettare la loro scadenza.
    token_version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailVerification(Base):
    """Codice monouso spedito via email per provare che l'indirizzo è di chi si registra."""

    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True)
    # Il codice è corto (6 caratteri = bassa entropia): in DB va solo l'hash bcrypt,
    # così un dump del database non regala i codici in circolazione.
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True))
    # Tetto ai tentativi: senza, 6 caratteri sarebbero forzabili a tappeto.
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    """Sessione persistente per dispositivo. In DB solo l'hash del token."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String, unique=True, nullable=False, index=True)
    # I token nati da rotazioni successive condividono la famiglia: se ne viene
    # riusato uno vecchio, si revoca l'intera catena.
    family_id = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    user_agent = Column(String)


class Watched(Base):
    __tablename__ = "watched"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    poster_path = Column(String)
    vote_average = Column(Float)
    overview = Column(Text)
    genre_ids = Column(Text)  # stringa JSON: "[28,12,53]"
    release_date = Column(String)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    rating = Column(Integer)  # voto personale 1-10

    __table_args__ = (
        # user_id DEVE far parte del vincolo: senza, il secondo utente che segna un
        # film già segnato da un altro prenderebbe un 409. È l'errore del piano
        # scritto in .claude/roadmap.md, che proponeva solo di aggiungere la colonna.
        UniqueConstraint(
            "user_id", "tmdb_id", "media_type", name="uq_watched_user_tmdb_media"
        ),
        CheckConstraint("media_type IN ('movie','tv')", name="ck_watched_media_type"),
    )
