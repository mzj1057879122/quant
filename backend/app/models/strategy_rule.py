from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, Numeric, Text, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StrategyRule(Base):
    __tablename__ = "strategy_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ruleKey: Mapped[str] = mapped_column(
        "rule_key", String(50), nullable=False, unique=True, comment="规则键名"
    )
    ruleValue: Mapped[Decimal] = mapped_column(
        "rule_value", Numeric(10, 4), nullable=False, comment="规则数值"
    )
    ruleDesc: Mapped[str | None] = mapped_column(
        "rule_desc", Text, nullable=True, comment="规则说明"
    )
    category: Mapped[str | None] = mapped_column(
        "category", String(30), nullable=True, comment="分类：volume/price/sector/anchor/confidence"
    )
    isActive: Mapped[int] = mapped_column(
        "is_active", SmallInteger, nullable=False, default=1
    )
    updatedBy: Mapped[str] = mapped_column(
        "updated_by", String(50), nullable=False, default="system", comment="最后更新者：system/xiaozhua"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
