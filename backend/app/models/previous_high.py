from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, Integer, Date, DateTime, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PreviousHigh(Base):
    __tablename__ = "previous_high"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    highPrice: Mapped[Decimal] = mapped_column(
        "high_price", Numeric(10, 3), nullable=False, comment="前高价格"
    )
    highDate: Mapped[date] = mapped_column(
        "high_date", Date, nullable=False, comment="前高日期"
    )
    lookbackDays: Mapped[int] = mapped_column(
        "lookback_days", Integer, nullable=False, comment="回溯天数"
    )
    highType: Mapped[str] = mapped_column(
        "high_type", String(20), nullable=False, comment="前高类型 local_high/history_high"
    )
    status: Mapped[str] = mapped_column(
        "status", String(20), nullable=False, default="active",
        comment="状态 active/broken/expired"
    )
    brokenDate: Mapped[date | None] = mapped_column(
        "broken_date", Date, nullable=True, comment="被突破日期"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_stock_status", "stock_code", "status"),
        Index("idx_stock_high_date", "stock_code", "high_date"),
    )
