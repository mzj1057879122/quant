from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, Integer, Date, DateTime, Numeric, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BreakoutAnalysis(Base):
    __tablename__ = "breakout_analysis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, unique=True, comment="股票代码"
    )
    previousHighId: Mapped[int | None] = mapped_column(
        "previous_high_id", BigInteger, nullable=True, comment="关联当前前高ID"
    )
    currentHighPrice: Mapped[Decimal | None] = mapped_column(
        "current_high_price", Numeric(10, 3), nullable=True, comment="当前前高价格"
    )
    currentHighDate: Mapped[date | None] = mapped_column(
        "current_high_date", Date, nullable=True, comment="当前前高日期"
    )
    totalApproachCount: Mapped[int] = mapped_column(
        "total_approach_count", Integer, nullable=False, default=0, comment="总接近次数"
    )
    breakoutSuccessCount: Mapped[int] = mapped_column(
        "breakout_success_count", Integer, nullable=False, default=0, comment="突破成功次数"
    )
    breakoutFailCount: Mapped[int] = mapped_column(
        "breakout_fail_count", Integer, nullable=False, default=0, comment="突破失败次数"
    )
    successRate: Mapped[Decimal | None] = mapped_column(
        "success_rate", Numeric(5, 2), nullable=True, comment="突破成功率"
    )
    historyEvents: Mapped[str | None] = mapped_column(
        "history_events", Text, nullable=True, comment="历史事件详情JSON"
    )
    extraData: Mapped[str | None] = mapped_column(
        "extra_data", Text, nullable=True, comment="扩展数据JSON（消息面等）"
    )
    analyzedAt: Mapped[datetime | None] = mapped_column(
        "analyzed_at", DateTime, nullable=True, comment="分析时间"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_ba_stock_code", "stock_code"),
    )
