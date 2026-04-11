"""add limit_up_diagram table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'limit_up_diagram',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日期'),
        sa.Column('diagram_url', sa.String(length=500), nullable=False, comment='韭研公社涨停简图OSS地址'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', name='uk_diagram_date'),
    )


def downgrade() -> None:
    op.drop_table('limit_up_diagram')
