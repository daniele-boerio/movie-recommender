"""liste personalizzate: custom_lists e list_items

Revision ID: f3a9c1d5e7b2
Revises: e8f1a2b3c4d5
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c1d5e7b2"
down_revision: Union[str, None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_custom_lists_user_id"), "custom_lists", ["user_id"], unique=False
    )

    op.create_table(
        "list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("poster_path", sa.String(), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("release_date", sa.String(), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["list_id"], ["custom_lists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "list_id", "tmdb_id", "media_type", name="uq_list_item"
        ),
        sa.CheckConstraint(
            "media_type IN ('movie','tv')", name="ck_list_item_media_type"
        ),
    )
    op.create_index(
        op.f("ix_list_items_list_id"), "list_items", ["list_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_list_items_list_id"), table_name="list_items")
    op.drop_table("list_items")
    op.drop_index(op.f("ix_custom_lists_user_id"), table_name="custom_lists")
    op.drop_table("custom_lists")
