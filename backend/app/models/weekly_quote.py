from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, Date, DateTime, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeeklyQuote(Base):
    __tablename__ = "weekly_quote"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    weekStart: Mapped[date] = mapped_column(
        "week_start", Date, nullable=False, comment="周一日期"
    )
    openPrice: Mapped[Decimal] = mapped_column(
        "open_price", Numeric(10, 3), nullable=False, comment="周开盘价（周一开盘）"
    )
    closePrice: Mapped[Decimal] = mapped_column(
        "close_price", Numeric(10, 3), nullable=False, comment="周收盘价（周五收盘）"
    )
    highPrice: Mapped[Decimal] = mapped_column(
        "high_price", Numeric(10, 3), nullable=False, comment="周最高价"
    )
    lowPrice: Mapped[Decimal] = mapped_column(
        "low_price", Numeric(10, 3), nullable=False, comment="周最低价"
    )
    volume: Mapped[int] = mapped_column(
        "volume", BigInteger, nullable=False, comment="周成交量之和"
    )
    expma5: Mapped[Decimal | None] = mapped_column(
        "expma5", Numeric(10, 3), nullable=True, comment="周线EXPMA5"
    )
    expma13: Mapped[Decimal | None] = mapped_column(
        "expma13", Numeric(10, 3), nullable=True, comment="周线EXPMA13"
    )
    expma34: Mapped[Decimal | None] = mapped_column(
        "expma34", Numeric(10, 3), nullable=True, comment="周线EXPMA34"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("uk_weekly_stock_week", "stock_code", "week_start", unique=True),
        Index("idx_weekly_week_start", "week_start"),
    )
