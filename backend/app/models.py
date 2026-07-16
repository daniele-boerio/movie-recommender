"""Modelli SQLAlchemy."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from .database import Base


class Watched(Base):
    __tablename__ = "watched"

    id = Column(Integer, primary_key=True)
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
        UniqueConstraint("tmdb_id", "media_type", name="uq_watched_tmdb_media"),
        CheckConstraint("media_type IN ('movie','tv')", name="ck_watched_media_type"),
    )
