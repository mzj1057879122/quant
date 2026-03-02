from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, SmallInteger, Date, DateTime, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Signal(Base):
    __tablename__ = "signal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    stockName: Mapped[str] = mapped_column(
        "stock_name", String(50), nullable=False, comment="股票名称"
    )
    signalType: Mapped[str] = mapped_column(
        "signal_type", String(30), nullable=False, comment="信号类型"
    )
    signalDate: Mapped[date] = mapped_column(
        "signal_date", Date, nullable=False, comment="信号日期"
    )
    previousHighId: Mapped[int | None] = mapped_column(
        "previous_high_id", BigInteger, nullable=True, comment="关联前高ID"
    )
    previousHighPrice: Mapped[Decimal] = mapped_column(
        "previous_high_price", Numeric(10, 3), nullable=False, comment="前高价格"
    )
    triggerPrice: Mapped[Decimal] = mapped_column(
        "trigger_price", Numeric(10, 3), nullable=False, comment="触发价格"
    )
    closePrice: Mapped[Decimal] = mapped_column(
        "close_price", Numeric(10, 3), nullable=False, comment="当日收盘价"
    )
    description: Mapped[str | None] = mapped_column(
        "description", String(500), nullable=True, comment="信号描述"
    )
    isNotified: Mapped[int] = mapped_column(
        "is_notified", SmallInteger, nullable=False, default=0, comment="是否已推送"
    )
    successRate: Mapped[Decimal | None] = mapped_column(
        "success_rate", Numeric(5, 2), nullable=True, comment="历史突破成功率"
    )
    isRead: Mapped[int] = mapped_column(
        "is_read", SmallInteger, nullable=False, default=0, comment="是否已读"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("idx_stock_signal_date", "stock_code", "signal_date"),
        Index("idx_signal_type", "signal_type"),
        Index("idx_is_notified", "is_notified"),
        Index("idx_signal_date", "signal_date"),
    )
