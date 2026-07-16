"""schema iniziale: tabella watched

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watched",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("poster_path", sa.String(), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("genre_ids", sa.Text(), nullable=True),
        sa.Column("release_date", sa.String(), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id", "media_type", name="uq_watched_tmdb_media"),
        sa.CheckConstraint("media_type IN ('movie','tv')", name="ck_watched_media_type"),
    )


def downgrade() -> None:
    op.drop_table("watched")
