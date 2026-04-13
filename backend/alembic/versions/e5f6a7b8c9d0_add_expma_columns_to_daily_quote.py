"""add expma columns to daily_quote

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('daily_quote', sa.Column('expma5', sa.Numeric(10, 3), nullable=True, comment='EXPMA5'))
    op.add_column('daily_quote', sa.Column('expma13', sa.Numeric(10, 3), nullable=True, comment='EXPMA13'))
    op.add_column('daily_quote', sa.Column('expma34', sa.Numeric(10, 3), nullable=True, comment='EXPMA34'))
    op.add_column('daily_quote', sa.Column('expma89', sa.Numeric(10, 3), nullable=True, comment='EXPMA89'))


def downgrade() -> None:
    op.drop_column('daily_quote', 'expma89')
    op.drop_column('daily_quote', 'expma34')
    op.drop_column('daily_quote', 'expma13')
    op.drop_column('daily_quote', 'expma5')
