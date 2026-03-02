from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, Date, DateTime, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyQuote(Base):
    __tablename__ = "daily_quote"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    tradeDate: Mapped[date] = mapped_column(
        "trade_date", Date, nullable=False, comment="交易日期"
    )
    openPrice: Mapped[Decimal] = mapped_column(
        "open_price", Numeric(10, 3), nullable=False, comment="开盘价"
    )
    closePrice: Mapped[Decimal] = mapped_column(
        "close_price", Numeric(10, 3), nullable=False, comment="收盘价"
    )
    highPrice: Mapped[Decimal] = mapped_column(
        "high_price", Numeric(10, 3), nullable=False, comment="最高价"
    )
    lowPrice: Mapped[Decimal] = mapped_column(
        "low_price", Numeric(10, 3), nullable=False, comment="最低价"
    )
    volume: Mapped[int] = mapped_column(
        "volume", BigInteger, nullable=False, comment="成交量"
    )
    turnover: Mapped[Decimal] = mapped_column(
        "turnover", Numeric(20, 2), nullable=False, comment="成交额"
    )
    changePct: Mapped[Decimal | None] = mapped_column(
        "change_pct", Numeric(8, 4), nullable=True, comment="涨跌幅"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("uk_stock_date", "stock_code", "trade_date", unique=True),
        Index("idx_trade_date", "trade_date"),
    )
