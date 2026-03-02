from datetime import date, datetime

from sqlalchemy import String, BigInteger, Integer, Text, Date, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(
        "title", String(200), nullable=True, comment="文章标题"
    )
    content: Mapped[str] = mapped_column(
        "content", Text, nullable=False, comment="文章内容"
    )
    author: Mapped[str | None] = mapped_column(
        "author", String(100), nullable=True, comment="作者"
    )
    source: Mapped[str | None] = mapped_column(
        "source", String(50), nullable=True, comment="来源"
    )
    sourceUrl: Mapped[str | None] = mapped_column(
        "source_url", String(500), nullable=True, comment="原文链接"
    )
    articleDate: Mapped[date] = mapped_column(
        "article_date", Date, nullable=False, default=date.today, comment="文章日期"
    )
    status: Mapped[str] = mapped_column(
        "status", String(20), nullable=False, default="pending", comment="处理状态"
    )
    resultSummary: Mapped[str | None] = mapped_column(
        "result_summary", Text, nullable=True, comment="处理结果摘要"
    )
    updatedFiles: Mapped[str | None] = mapped_column(
        "updated_files", String(500), nullable=True, comment="更新的文件列表"
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
        Index("idx_article_status", "status"),
        Index("idx_article_created", "created_at"),
    )
