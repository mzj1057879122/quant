from datetime import datetime

from sqlalchemy import String, Integer, SmallInteger, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Stock(Base):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, unique=True, comment="股票代码"
    )
    stockName: Mapped[str] = mapped_column(
        "stock_name", String(50), nullable=False, comment="股票名称"
    )
    market: Mapped[str] = mapped_column(
        "market", String(10), nullable=False, comment="市场 sh/sz/bj"
    )
    industry: Mapped[str | None] = mapped_column(
        "industry", String(50), nullable=True, comment="所属行业"
    )
    isActive: Mapped[int] = mapped_column(
        "is_active", SmallInteger, nullable=False, default=1, comment="是否活跃"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("uk_stock_code", "stock_code", unique=True),
    )
