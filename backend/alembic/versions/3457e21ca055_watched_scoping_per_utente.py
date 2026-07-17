"""watched: scoping per utente

Revision ID: 3457e21ca055
Revises: 360b817f0ec7
Create Date: 2026-07-17 02:10:35.911959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3457e21ca055'
down_revision: Union[str, None] = '360b817f0ec7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # La colonna nasce NOT NULL senza default: regge perché `watched` è vuota. Su una
    # tabella già popolata servirebbe prima assegnare le righe esistenti a un utente.
    op.add_column('watched', sa.Column('user_id', sa.Integer(), nullable=False))

    # Il pezzo che conta: il vecchio vincolo era su (tmdb_id, media_type), quindi due
    # utenti non avrebbero potuto avere lo stesso film in lista (il secondo prendeva
    # un 409). Va sostituito, non affiancato.
    op.drop_constraint(op.f('uq_watched_tmdb_media'), 'watched', type_='unique')
    op.create_unique_constraint(
        'uq_watched_user_tmdb_media', 'watched', ['user_id', 'tmdb_id', 'media_type']
    )

    op.create_index(op.f('ix_watched_user_id'), 'watched', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_watched_user_id', 'watched', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_watched_user_id', 'watched', type_='foreignkey')
    op.drop_constraint('uq_watched_user_tmdb_media', 'watched', type_='unique')
    op.drop_index(op.f('ix_watched_user_id'), table_name='watched')
    op.create_unique_constraint(
        op.f('uq_watched_tmdb_media'), 'watched', ['tmdb_id', 'media_type']
    )
    op.drop_column('watched', 'user_id')
