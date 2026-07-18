"""episode_progress: tracking per-episodio delle serie

Revision ID: d7e2b9a4c1f5
Revises: c3d9f1a4b2e6
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e2b9a4c1f5"
down_revision: Union[str, None] = "c3d9f1a4b2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "episode_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column(
            "watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "tmdb_id",
            "season_number",
            "episode_number",
            name="uq_episode_progress",
        ),
    )
    op.create_index(
        op.f("ix_episode_progress_user_id"),
        "episode_progress",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_episode_progress_user_id"), table_name="episode_progress"
    )
    op.drop_table("episode_progress")
