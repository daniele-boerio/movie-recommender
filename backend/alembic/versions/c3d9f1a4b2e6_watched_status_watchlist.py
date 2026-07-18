"""watched: colonna status per la watchlist "da vedere"

Revision ID: c3d9f1a4b2e6
Revises: 3457e21ca055
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d9f1a4b2e6"
down_revision: Union[str, None] = "3457e21ca055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default='watched': le righe già presenti sono tutte "viste", quindi la
    # colonna può nascere NOT NULL anche su tabella popolata senza backfill manuale.
    op.add_column(
        "watched",
        sa.Column(
            "status", sa.String(), nullable=False, server_default="watched"
        ),
    )
    # Il CHECK va nella migration a mano: Alembic non lo autogenera.
    op.create_check_constraint(
        "ck_watched_status", "watched", "status IN ('watched','watchlist')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_watched_status", "watched", type_="check")
    op.drop_column("watched", "status")
