from datetime import date, datetime

from sqlalchemy import String, BigInteger, Integer, Float, Boolean, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockHeat(Base):
    __tablename__ = "stock_heat"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stockCode: Mapped[str] = mapped_column(
        "stock_code", String(10), nullable=False, comment="股票代码"
    )
    heatDate: Mapped[date] = mapped_column(
        "heat_date", Date, nullable=False, comment="日期"
    )
    xqFollowCount: Mapped[int | None] = mapped_column(
        "xq_follow_count", BigInteger, nullable=True, comment="雪球关注数"
    )
    xqFollowRank: Mapped[int | None] = mapped_column(
        "xq_follow_rank", Integer, nullable=True, comment="雪球关注排名"
    )
    xqTweetCount: Mapped[int | None] = mapped_column(
        "xq_tweet_count", BigInteger, nullable=True, comment="雪球讨论数"
    )
    xqTweetRank: Mapped[int | None] = mapped_column(
        "xq_tweet_rank", Integer, nullable=True, comment="雪球讨论排名"
    )
    baiduHot: Mapped[bool] = mapped_column(
        "baidu_hot", Boolean, nullable=False, default=False, comment="是否在百度热搜"
    )
    heatScore: Mapped[int] = mapped_column(
        "heat_score", Integer, nullable=False, default=0, comment="综合热度得分(0-100)"
    )
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("stock_code", "heat_date", name="uq_stock_heat_code_date"),
        Index("idx_heat_date", "heat_date"),
        Index("idx_heat_score", "heat_score"),
    )
