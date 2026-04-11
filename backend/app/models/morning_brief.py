from datetime import date, datetime

from sqlalchemy import String, Integer, Text, Date, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MorningBrief(Base):
    __tablename__ = "morning_brief"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    briefDate: Mapped[date] = mapped_column(
        "brief_date", Date, nullable=False, comment="盘前日期"
    )
    source: Mapped[str | None] = mapped_column(
        "source", String(20), nullable=True, comment="briefA/briefB"
    )
    rawContent: Mapped[str | None] = mapped_column(
        "raw_content", Text().with_variant(Text(length=4294967295), "mysql"), nullable=True, comment="原始内容"
    )
    aiSummary: Mapped[str | None] = mapped_column(
        "ai_summary", Text, nullable=True, comment="AI摘要"
    )
    hotSectors: Mapped[str | None] = mapped_column(
        "hot_sectors", Text, nullable=True, comment="热门板块（JSON数组）"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("brief_date", "source", name="uq_brief_date_source"),
        Index("idx_brief_date", "brief_date"),
    )
