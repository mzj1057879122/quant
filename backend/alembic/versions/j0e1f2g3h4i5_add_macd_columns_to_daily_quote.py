"""add macd columns to daily_quote

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-04-12 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'j0e1f2g3h4i5'
down_revision: Union[str, None] = 'i9d0e1f2g3h4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('daily_quote', sa.Column('macd_diff', sa.Numeric(10, 4), nullable=True, comment='MACD DIF线=EMA12-EMA26'))
    op.add_column('daily_quote', sa.Column('macd_dea', sa.Numeric(10, 4), nullable=True, comment='MACD DEA信号线=EMA9(DIF)'))
    op.add_column('daily_quote', sa.Column('macd_bar', sa.Numeric(10, 4), nullable=True, comment='MACD柱=(DIF-DEA)*2'))


def downgrade() -> None:
    op.drop_column('daily_quote', 'macd_bar')
    op.drop_column('daily_quote', 'macd_dea')
    op.drop_column('daily_quote', 'macd_diff')
