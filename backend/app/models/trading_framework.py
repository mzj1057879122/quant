from datetime import datetime

from sqlalchemy import String, BigInteger, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TradingFramework(Base):
    __tablename__ = "trading_framework"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(
        "version", Integer, nullable=False, comment="版本号递增"
    )
    status: Mapped[str] = mapped_column(
        "status", String(20), nullable=False, default="pending", comment="处理状态"
    )
    knowledgeCount: Mapped[int] = mapped_column(
        "knowledge_count", Integer, nullable=False, default=0, comment="贡献的心得数"
    )
    frameworkContent: Mapped[str | None] = mapped_column(
        "framework_content", Text, nullable=True, comment="框架内容JSON"
    )
    rawOutput: Mapped[str | None] = mapped_column(
        "raw_output", Text, nullable=True, comment="Claude原始输出"
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

    __table_args__ = (
        Index("idx_framework_version", "version"),
        Index("idx_framework_status", "status"),
    )
