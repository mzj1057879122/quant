"""add strategy_rules table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11 12:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'strategy_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule_key', sa.String(length=50), nullable=False, comment='规则键名'),
        sa.Column('rule_value', sa.Numeric(precision=10, scale=4), nullable=False, comment='规则数值'),
        sa.Column('rule_desc', sa.Text(), nullable=True, comment='规则说明'),
        sa.Column('category', sa.String(length=30), nullable=True, comment='分类：volume/price/sector/anchor/confidence'),
        sa.Column('is_active', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('updated_by', sa.String(length=50), nullable=False, server_default='system', comment='最后更新者：system/xiaozhua'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_key', name='uq_strategy_rule_key'),
    )

    op.bulk_insert(
        sa.table(
            'strategy_rules',
            sa.column('rule_key', sa.String),
            sa.column('rule_value', sa.Numeric),
            sa.column('rule_desc', sa.Text),
            sa.column('category', sa.String),
            sa.column('is_active', sa.SmallInteger),
            sa.column('updated_by', sa.String),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        ),
        [
            {'rule_key': 'volume_ratio_min',   'rule_value': 1.8,  'rule_desc': '启动信号：放量倍数下限',             'category': 'volume',     'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'gain_pct_min',        'rule_value': 5.0,  'rule_desc': '启动信号：涨幅下限(%)',             'category': 'price',      'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'breakout_days',       'rule_value': 20,   'rule_desc': '突破前N日最高价',                   'category': 'price',      'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'anchor_break_pct',    'rule_value': 0,    'rule_desc': '跌破锚位判定阈值(%)',               'category': 'anchor',     'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'shrink_ratio',        'rule_value': 0.5,  'rule_desc': '缩量洗盘：成交量/前日比率上限',    'category': 'volume',     'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'extreme_vol_ratio',   'rule_value': 3.0,  'rule_desc': '极值量：成交量/均量倍数',          'category': 'volume',     'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'conf_high_signals',   'rule_value': 2,    'rule_desc': '高置信：需要的正向信号数',         'category': 'confidence', 'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'conf_mid_signals',    'rule_value': 1,    'rule_desc': '中置信：需要的正向信号数',         'category': 'confidence', 'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'sector_retreat_days', 'rule_value': 2,    'rule_desc': '板块退潮：涨停家数连续递减天数',  'category': 'sector',     'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'rule_key': 'dynamic_anchor_vol',  'rule_value': 1.8,  'rule_desc': '动态锚位上移：放量倍数条件',      'category': 'anchor',     'is_active': 1, 'updated_by': 'system', 'created_at': datetime.now(), 'updated_at': datetime.now()},
        ],
    )


def downgrade() -> None:
    op.drop_table('strategy_rules')
