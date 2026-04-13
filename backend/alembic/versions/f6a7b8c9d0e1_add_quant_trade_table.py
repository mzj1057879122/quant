"""add quant_trade table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'quant_trade',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码'),
        sa.Column('signal_date', sa.Date(), nullable=False, comment='启动日'),
        sa.Column('anchor_price', sa.Numeric(precision=10, scale=3), nullable=False, comment='锚位（启动日最低价）'),
        sa.Column('entry_price', sa.Numeric(precision=10, scale=3), nullable=False, comment='进场价（启动日收盘价）'),
        sa.Column('entry_date', sa.Date(), nullable=False, comment='进场日期'),
        sa.Column('exit_price', sa.Numeric(precision=10, scale=3), nullable=True, comment='出场价'),
        sa.Column('exit_date', sa.Date(), nullable=True, comment='出场日期'),
        sa.Column('exit_reason', sa.String(length=20), nullable=True,
                  comment='出场原因: volume_top/stop_loss/time_stop/data_end'),
        sa.Column('return_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='收益率(%)'),
        sa.Column('hold_days', sa.Integer(), nullable=True, comment='持仓天数'),
        sa.Column('backtest_run_id', sa.String(length=20), nullable=False, comment='回测批次标识'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_qt_stock_code', 'quant_trade', ['stock_code'], unique=False)
    op.create_index('idx_qt_signal_date', 'quant_trade', ['signal_date'], unique=False)
    op.create_index('idx_qt_run_id', 'quant_trade', ['backtest_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_qt_run_id', table_name='quant_trade')
    op.drop_index('idx_qt_signal_date', table_name='quant_trade')
    op.drop_index('idx_qt_stock_code', table_name='quant_trade')
    op.drop_table('quant_trade')
