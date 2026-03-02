"""add trading_knowledge and trading_framework tables

Revision ID: e30ac5ed6fa4
Revises: c13a655a0b9c
Create Date: 2026-03-01 06:46:43.358127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e30ac5ed6fa4'
down_revision: Union[str, None] = 'c13a655a0b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trading_knowledge',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(200), nullable=False, comment='标题'),
        sa.Column('author', sa.String(100), nullable=True, comment='作者/博主'),
        sa.Column('content', sa.Text(), nullable=False, comment='原文内容'),
        sa.Column('source', sa.String(50), nullable=True, comment='来源'),
        sa.Column('source_url', sa.String(500), nullable=True, comment='原文链接'),
        sa.Column('category', sa.String(50), nullable=True, comment='分类'),
        sa.Column('status', sa.String(20), nullable=False, comment='处理状态'),
        sa.Column('extracted_principles', sa.Text(), nullable=True, comment='提取的交易原则JSON'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('process_duration', sa.Integer(), nullable=True, comment='耗时(秒)'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_knowledge_status', 'trading_knowledge', ['status'])
    op.create_index('idx_knowledge_category', 'trading_knowledge', ['category'])
    op.create_index('idx_knowledge_created', 'trading_knowledge', ['created_at'])

    op.create_table(
        'trading_framework',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, comment='版本号递增'),
        sa.Column('status', sa.String(20), nullable=False, comment='处理状态'),
        sa.Column('knowledge_count', sa.Integer(), nullable=False, comment='贡献的心得数'),
        sa.Column('framework_content', sa.Text(), nullable=True, comment='框架内容JSON'),
        sa.Column('raw_output', sa.Text(), nullable=True, comment='Claude原始输出'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('process_duration', sa.Integer(), nullable=True, comment='耗时(秒)'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_framework_version', 'trading_framework', ['version'])
    op.create_index('idx_framework_status', 'trading_framework', ['status'])


def downgrade() -> None:
    op.drop_table('trading_framework')
    op.drop_table('trading_knowledge')
