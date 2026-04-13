from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, Integer, Date, DateTime, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QuantTrade(Base):
    __tablename__ = "quant_trade"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    signalDate: Mapped[date] = mapped_column(
        "signal_date", Date, nullable=False, comment="启动日"
    )
    anchorPrice: Mapped[Decimal] = mapped_column(
        "anchor_price", Numeric(10, 3), nullable=False, comment="锚位（启动日最低价）"
    )
    entryPrice: Mapped[Decimal] = mapped_column(
        "entry_price", Numeric(10, 3), nullable=False, comment="进场价（启动日收盘价）"
    )
    entryDate: Mapped[date] = mapped_column(
        "entry_date", Date, nullable=False, comment="进场日期"
    )
    exitPrice: Mapped[Decimal | None] = mapped_column(
        "exit_price", Numeric(10, 3), nullable=True, comment="出场价"
    )
    exitDate: Mapped[date | None] = mapped_column(
        "exit_date", Date, nullable=True, comment="出场日期"
    )
    exitReason: Mapped[str | None] = mapped_column(
        "exit_reason", String(20), nullable=True,
        comment="出场原因: volume_top/stop_loss/time_stop/data_end"
    )
    returnPct: Mapped[Decimal | None] = mapped_column(
        "return_pct", Numeric(8, 4), nullable=True, comment="收益率(%)"
    )
    holdDays: Mapped[int | None] = mapped_column(
        "hold_days", Integer, nullable=True, comment="持仓天数"
    )
    backtestRunId: Mapped[str] = mapped_column(
        "backtest_run_id", String(20), nullable=False, comment="回测批次标识"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("idx_qt_stock_code", "stock_code"),
        Index("idx_qt_signal_date", "signal_date"),
        Index("idx_qt_run_id", "backtest_run_id"),
    )
