"""add weekly_quote table

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-04-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i9d0e1f2g3h4'
down_revision: Union[str, None] = 'h8c9d0e1f2g3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'weekly_quote',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码'),
        sa.Column('week_start', sa.Date(), nullable=False, comment='周一日期'),
        sa.Column('open_price', sa.Numeric(10, 3), nullable=False, comment='周开盘价（周一开盘）'),
        sa.Column('close_price', sa.Numeric(10, 3), nullable=False, comment='周收盘价（周五收盘）'),
        sa.Column('high_price', sa.Numeric(10, 3), nullable=False, comment='周最高价'),
        sa.Column('low_price', sa.Numeric(10, 3), nullable=False, comment='周最低价'),
        sa.Column('volume', sa.BigInteger(), nullable=False, comment='周成交量之和'),
        sa.Column('expma5', sa.Numeric(10, 3), nullable=True, comment='周线EXPMA5'),
        sa.Column('expma13', sa.Numeric(10, 3), nullable=True, comment='周线EXPMA13'),
        sa.Column('expma34', sa.Numeric(10, 3), nullable=True, comment='周线EXPMA34'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('uk_weekly_stock_week', 'weekly_quote', ['stock_code', 'week_start'], unique=True)
    op.create_index('idx_weekly_week_start', 'weekly_quote', ['week_start'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_weekly_week_start', table_name='weekly_quote')
    op.drop_index('uk_weekly_stock_week', table_name='weekly_quote')
    op.drop_table('weekly_quote')
