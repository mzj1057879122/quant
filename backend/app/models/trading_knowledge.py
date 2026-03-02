from datetime import datetime

from sqlalchemy import String, BigInteger, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TradingKnowledge(Base):
    __tablename__ = "trading_knowledge"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        "title", String(200), nullable=False, comment="标题"
    )
    author: Mapped[str | None] = mapped_column(
        "author", String(100), nullable=True, comment="作者/博主"
    )
    content: Mapped[str] = mapped_column(
        "content", Text, nullable=False, comment="原文内容"
    )
    source: Mapped[str | None] = mapped_column(
        "source", String(50), nullable=True, comment="来源"
    )
    sourceUrl: Mapped[str | None] = mapped_column(
        "source_url", String(500), nullable=True, comment="原文链接"
    )
    category: Mapped[str | None] = mapped_column(
        "category", String(50), nullable=True, comment="分类"
    )
    status: Mapped[str] = mapped_column(
        "status", String(20), nullable=False, default="pending", comment="处理状态"
    )
    extractedPrinciples: Mapped[str | None] = mapped_column(
        "extracted_principles", Text, nullable=True, comment="提取的交易原则JSON"
    )
    errorMessage: Mapped[str | None] = mapped_column(
        "error_message", Text, nullable=True, comment="错误信息"
    )
    processDuration: Mapped[int | None] = mapped_column(
        "process_duration", Integer, nullable=True, comment="耗时(秒)"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("idx_knowledge_status", "status"),
        Index("idx_knowledge_category", "category"),
        Index("idx_knowledge_created", "created_at"),
    )
