from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserConfig(Base):
    __tablename__ = "user_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    configKey: Mapped[str] = mapped_column(
        "config_key", String(100), nullable=False, unique=True, comment="配置键"
    )
    configValue: Mapped[str] = mapped_column(
        "config_value", Text, nullable=False, comment="配置值JSON"
    )
    description: Mapped[str | None] = mapped_column(
        "description", String(200), nullable=True, comment="配置说明"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("uk_config_key", "config_key", unique=True),
    )
