from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Text, Date, DateTime, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    stockName: Mapped[str] = mapped_column(
        "stock_name", String(50), nullable=False, comment="股票名称"
    )
    sector: Mapped[str | None] = mapped_column(
        "sector", String(50), nullable=True, comment="板块/题材"
    )
    addReason: Mapped[str | None] = mapped_column(
        "add_reason", Text, nullable=True, comment="加入原因"
    )
    status: Mapped[str] = mapped_column(
        "status", String(20), nullable=False, default="watching", comment="watching/holding/exited"
    )
    anchorPrice: Mapped[Decimal | None] = mapped_column(
        "anchor_price", Numeric(precision=10, scale=3), nullable=True, comment="锚位（启动日最低价）"
    )
    anchorDate: Mapped[date | None] = mapped_column(
        "anchor_date", Date, nullable=True, comment="锚位日期"
    )
    confidence: Mapped[str | None] = mapped_column(
        "confidence", String(10), nullable=True, comment="高/中/低"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("stock_code", name="uq_watchlist_code"),
    )
