"""add breakout_analysis table and signal success_rate

Revision ID: c13a655a0b9c
Revises:
Create Date: 2026-02-28 03:33:49.528024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = 'c13a655a0b9c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa_inspect(bind)
    existing_tables = insp.get_table_names()

    # 创建 breakout_analysis 表（如果不存在）
    if 'breakout_analysis' not in existing_tables:
        op.create_table(
            'breakout_analysis',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('stock_code', sa.String(10), nullable=False, comment='股票代码'),
            sa.Column('previous_high_id', sa.BigInteger(), nullable=True, comment='关联当前前高ID'),
            sa.Column('current_high_price', sa.Numeric(10, 3), nullable=True, comment='当前前高价格'),
            sa.Column('current_high_date', sa.Date(), nullable=True, comment='当前前高日期'),
            sa.Column('total_approach_count', sa.Integer(), nullable=False, server_default='0', comment='总接近次数'),
            sa.Column('breakout_success_count', sa.Integer(), nullable=False, server_default='0', comment='突破成功次数'),
            sa.Column('breakout_fail_count', sa.Integer(), nullable=False, server_default='0', comment='突破失败次数'),
            sa.Column('success_rate', sa.Numeric(5, 2), nullable=True, comment='突破成功率'),
            sa.Column('history_events', sa.Text(), nullable=True, comment='历史事件详情JSON'),
            sa.Column('extra_data', sa.Text(), nullable=True, comment='扩展数据JSON（消息面等）'),
            sa.Column('analyzed_at', sa.DateTime(), nullable=True, comment='分析时间'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('stock_code'),
        )
        op.create_index('idx_ba_stock_code', 'breakout_analysis', ['stock_code'])

    # signal 表新增 success_rate 字段
    existing_columns = [c['name'] for c in insp.get_columns('signal')]
    if 'success_rate' not in existing_columns:
        op.add_column('signal', sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=True, comment='历史突破成功率'))


def downgrade() -> None:
    op.drop_column('signal', 'success_rate')
    op.drop_index('idx_ba_stock_code', table_name='breakout_analysis')
    op.drop_table('breakout_analysis')
