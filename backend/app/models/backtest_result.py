from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, BigInteger, SmallInteger, Text, Date, DateTime, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BacktestResult(Base):
    __tablename__ = "backtest_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    stockName: Mapped[str | None] = mapped_column(
        "stock_name", String(50), nullable=True, comment="股票名称"
    )
    predictDate: Mapped[date] = mapped_column(
        "predict_date", Date, nullable=False, comment="预测日期"
    )
    version: Mapped[str] = mapped_column(
        "version", String(10), nullable=False, default="v2", comment="v1/v2"
    )
    technicalSignal: Mapped[str | None] = mapped_column(
        "technical_signal", Text, nullable=True, comment="技术面信号描述"
    )
    newsSignal: Mapped[str | None] = mapped_column(
        "news_signal", Text, nullable=True, comment="消息面信号描述"
    )
    prediction: Mapped[str | None] = mapped_column(
        "prediction", Text, nullable=True, comment="综合预测"
    )
    confidence: Mapped[str | None] = mapped_column(
        "confidence", String(10), nullable=True, comment="高/中/低"
    )
    actualResult: Mapped[str | None] = mapped_column(
        "actual_result", Text, nullable=True, comment="实际结果"
    )
    isCorrect: Mapped[int | None] = mapped_column(
        "is_correct", SmallInteger, nullable=True, comment="1=对 0=错"
    )
    actualChangePct: Mapped[Decimal | None] = mapped_column(
        "actual_change_pct", Numeric(precision=8, scale=4), nullable=True, comment="实际涨跌幅"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("idx_backtest_stock_date", "stock_code", "predict_date"),
        Index("idx_backtest_version", "version"),
        Index("idx_backtest_correct", "is_correct"),
    )
