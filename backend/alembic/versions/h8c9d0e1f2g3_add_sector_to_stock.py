"""add sector to stock

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-04-12 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'h8c9d0e1f2g3'
down_revision: Union[str, None] = 'g7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'stock',
        sa.Column('sector', sa.String(length=100), nullable=True,
                  comment='所属板块（来自涨停板块数据最频繁出现的板块名）')
    )


def downgrade() -> None:
    op.drop_column('stock', 'sector')
