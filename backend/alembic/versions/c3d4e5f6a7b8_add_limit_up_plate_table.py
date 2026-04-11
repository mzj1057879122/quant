"""add limit_up_plate table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-11 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'limit_up_plate',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日期'),
        sa.Column('plate_name', sa.String(length=50), nullable=False, comment='板块名称'),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码（6位数字）'),
        sa.Column('stock_name', sa.String(length=20), nullable=False, comment='股票名称'),
        sa.Column('limit_up_days', sa.String(length=20), nullable=True, comment='几天几板，如3天3板'),
        sa.Column('limit_up_time', sa.String(length=20), nullable=True, comment='涨停时间'),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=True, comment='价格'),
        sa.Column('change_pct', sa.DECIMAL(precision=6, scale=2), nullable=True, comment='涨跌幅'),
        sa.Column('reason', sa.Text(), nullable=True, comment='涨停原因摘要'),
        sa.Column('sort_no', sa.Integer(), nullable=False, server_default='0', comment='排序号'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'stock_code', name='uk_date_code'),
    )
    op.create_index('idx_limit_up_plate_date', 'limit_up_plate', ['trade_date'])


def downgrade() -> None:
    op.drop_index('idx_limit_up_plate_date', table_name='limit_up_plate')
    op.drop_table('limit_up_plate')
