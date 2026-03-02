from datetime import date, datetime

from sqlalchemy import String, BigInteger, Integer, Text, Date, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailySummary(Base):
    __tablename__ = "daily_summary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    summaryDate: Mapped[date] = mapped_column(
        "summary_date", Date, nullable=False, unique=True, comment="汇总日期"
    )
    articleCount: Mapped[int] = mapped_column(
        "article_count", Integer, nullable=False, default=0, comment="当日文章数"
    )
    consensus: Mapped[str | None] = mapped_column(
        "consensus", Text, nullable=True, comment="多作者共识"
    )
    divergence: Mapped[str | None] = mapped_column(
        "divergence", Text, nullable=True, comment="分歧点"
    )
    stockViews: Mapped[str | None] = mapped_column(
        "stock_views", Text, nullable=True, comment="个股综合观点JSON"
    )
    sectorViews: Mapped[str | None] = mapped_column(
        "sector_views", Text, nullable=True, comment="板块综合观点JSON"
    )
    strategy: Mapped[str | None] = mapped_column(
        "strategy", Text, nullable=True, comment="明日应对策略"
    )
    evolution: Mapped[str | None] = mapped_column(
        "evolution", Text, nullable=True, comment="与前两天策略演变对比"
    )
    rawOutput: Mapped[str | None] = mapped_column(
        "raw_output", Text, nullable=True, comment="Claude原始输出"
    )
    status: Mapped[str] = mapped_column(
        "status", String(20), nullable=False, default="pending", comment="处理状态"
    )
    errorMessage: Mapped[str | None] = mapped_column(
        "error_message", Text, nullable=True, comment="错误信息"
    )
    processDuration: Mapped[int | None] = mapped_column(
        "process_duration", Integer, nullable=True, comment="处理耗时(秒)"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_summary_date", "summary_date"),
        Index("idx_summary_status", "status"),
    )
