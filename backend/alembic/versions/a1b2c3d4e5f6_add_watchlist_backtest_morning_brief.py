"""add watchlist backtest morning_brief tables

Revision ID: a1b2c3d4e5f6
Revises: 49783c9e80de
Create Date: 2026-04-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '49783c9e80de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='股票名称'),
        sa.Column('sector', sa.String(length=50), nullable=True, comment='板块/题材'),
        sa.Column('add_reason', sa.Text(), nullable=True, comment='加入原因'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='watching', comment='watching/holding/exited'),
        sa.Column('anchor_price', sa.Numeric(precision=10, scale=3), nullable=True, comment='锚位（启动日最低价）'),
        sa.Column('anchor_date', sa.Date(), nullable=True, comment='锚位日期'),
        sa.Column('confidence', sa.String(length=10), nullable=True, comment='高/中/低'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stock_code', name='uq_watchlist_code'),
    )

    op.create_table(
        'backtest_result',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=True, comment='股票名称'),
        sa.Column('predict_date', sa.Date(), nullable=False, comment='预测日期'),
        sa.Column('version', sa.String(length=10), nullable=False, server_default='v2', comment='v1/v2'),
        sa.Column('technical_signal', sa.Text(), nullable=True, comment='技术面信号描述'),
        sa.Column('news_signal', sa.Text(), nullable=True, comment='消息面信号描述'),
        sa.Column('prediction', sa.Text(), nullable=True, comment='综合预测'),
        sa.Column('confidence', sa.String(length=10), nullable=True, comment='高/中/低'),
        sa.Column('actual_result', sa.Text(), nullable=True, comment='实际结果'),
        sa.Column('is_correct', sa.SmallInteger(), nullable=True, comment='1=对 0=错'),
        sa.Column('actual_change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='实际涨跌幅'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_backtest_stock_date', 'backtest_result', ['stock_code', 'predict_date'], unique=False)
    op.create_index('idx_backtest_version', 'backtest_result', ['version'], unique=False)
    op.create_index('idx_backtest_correct', 'backtest_result', ['is_correct'], unique=False)

    op.create_table(
        'morning_brief',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('brief_date', sa.Date(), nullable=False, comment='盘前日期'),
        sa.Column('source', sa.String(length=20), nullable=True, comment='briefA/briefB'),
        sa.Column('raw_content', sa.Text(length=4294967295), nullable=True, comment='原始内容'),
        sa.Column('ai_summary', sa.Text(), nullable=True, comment='AI摘要'),
        sa.Column('hot_sectors', sa.Text(), nullable=True, comment='热门板块（JSON数组）'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('brief_date', 'source', name='uq_brief_date_source'),
    )
    op.create_index('idx_brief_date', 'morning_brief', ['brief_date'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_brief_date', table_name='morning_brief')
    op.drop_table('morning_brief')

    op.drop_index('idx_backtest_correct', table_name='backtest_result')
    op.drop_index('idx_backtest_version', table_name='backtest_result')
    op.drop_index('idx_backtest_stock_date', table_name='backtest_result')
    op.drop_table('backtest_result')

    op.drop_table('watchlist')
