"""liste condivise: tabella list_members

Revision ID: b4d6f8a0c2e4
Revises: a2c4e6f8b1d3
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d6f8a0c2e4"
down_revision: Union[str, None] = "a2c4e6f8b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "list_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["list_id"], ["custom_lists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("list_id", "user_id", name="uq_list_member"),
    )
    op.create_index(
        op.f("ix_list_members_list_id"), "list_members", ["list_id"], unique=False
    )
    op.create_index(
        op.f("ix_list_members_user_id"), "list_members", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_list_members_user_id"), table_name="list_members")
    op.drop_index(op.f("ix_list_members_list_id"), table_name="list_members")
    op.drop_table("list_members")
