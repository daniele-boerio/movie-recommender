"""watched: colonne review e watched_on (diario personale)

Revision ID: e8f1a2b3c4d5
Revises: d7e2b9a4c1f5
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "d7e2b9a4c1f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Entrambe nullable: le righe esistenti restano senza recensione né data, che è
    # esattamente il significato "non l'ho ancora scritta". Nessun backfill.
    op.add_column("watched", sa.Column("review", sa.Text(), nullable=True))
    op.add_column("watched", sa.Column("watched_on", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("watched", "watched_on")
    op.drop_column("watched", "review")
