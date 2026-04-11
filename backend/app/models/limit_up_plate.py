from datetime import datetime, date

from sqlalchemy import String, Integer, Date, DateTime, Text, DECIMAL, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LimitUpPlate(Base):
    __tablename__ = "limit_up_plate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tradeDate: Mapped[date] = mapped_column(
        "trade_date", Date, nullable=False, comment="交易日期"
    )
    plateName: Mapped[str] = mapped_column(
        "plate_name", String(50), nullable=False, comment="板块名称"
    )
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码（6位数字）"
    )
    stockName: Mapped[str] = mapped_column(
        "stock_name", String(20), nullable=False, comment="股票名称"
    )
    limitUpDays: Mapped[str | None] = mapped_column(
        "limit_up_days", String(20), nullable=True, comment="几天几板，如3天3板"
    )
    limitUpTime: Mapped[str | None] = mapped_column(
        "limit_up_time", String(20), nullable=True, comment="涨停时间"
    )
    price: Mapped[float | None] = mapped_column(
        "price", DECIMAL(10, 2), nullable=True, comment="价格"
    )
    changePct: Mapped[float | None] = mapped_column(
        "change_pct", DECIMAL(6, 2), nullable=True, comment="涨跌幅"
    )
    reason: Mapped[str | None] = mapped_column(
        "reason", Text, nullable=True, comment="涨停原因摘要"
    )
    sortNo: Mapped[int] = mapped_column(
        "sort_no", Integer, nullable=False, default=0, comment="排序号"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("trade_date", "stock_code", name="uk_date_code"),
        Index("idx_limit_up_plate_date", "trade_date"),
    )
