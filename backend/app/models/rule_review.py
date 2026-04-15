from datetime import date, datetime
from sqlalchemy import String, BigInteger, Text, Date, DateTime, Numeric, SmallInteger, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RuleReview(Base):
    __tablename__ = "rule_review"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reviewDate: Mapped[date] = mapped_column(
        "review_date", Date, nullable=False, comment="分析日期"
    )
    windowDays: Mapped[int] = mapped_column(
        "window_days", SmallInteger, nullable=False, default=30, comment="分析窗口天数"
    )
    totalPredictions: Mapped[int] = mapped_column(
        "total_predictions", BigInteger, nullable=False, default=0
    )
    overallWinRate: Mapped[float | None] = mapped_column(
        "overall_win_rate", Numeric(5, 2), nullable=True, comment="整体胜率"
    )
    # 各维度胜率（JSON字符串）
    bySignalType: Mapped[str | None] = mapped_column(
        "by_signal_type", Text, nullable=True, comment="按信号类型胜率 JSON"
    )
    byConfidence: Mapped[str | None] = mapped_column(
        "by_confidence", Text, nullable=True, comment="按置信度胜率 JSON"
    )
    byPrediction: Mapped[str | None] = mapped_column(
        "by_prediction", Text, nullable=True, comment="按预测方向胜率 JSON"
    )
    # Claude分析结论
    anomalies: Mapped[str | None] = mapped_column(
        "anomalies", Text, nullable=True, comment="发现的异常模式"
    )
    suggestions: Mapped[str | None] = mapped_column(
        "suggestions", Text, nullable=True, comment="规则修订建议"
    )
    alertLevel: Mapped[str | None] = mapped_column(
        "alert_level", String(10), nullable=True, comment="none/info/warn/critical"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("idx_rule_review_date", "review_date"),
    )
