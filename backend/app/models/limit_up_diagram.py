from datetime import datetime, date

from sqlalchemy import String, Integer, Date, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LimitUpDiagram(Base):
    __tablename__ = "limit_up_diagram"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tradeDate: Mapped[date] = mapped_column(
        "trade_date", Date, nullable=False, unique=True, comment="交易日期"
    )
    diagramUrl: Mapped[str] = mapped_column(
        "diagram_url", String(500), nullable=False, comment="韭研公社涨停简图OSS地址"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )
