from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class DailyQuoteResponse(BaseModel):
    id: int
    stockCode: str
    tradeDate: date
    openPrice: Decimal
    closePrice: Decimal
    highPrice: Decimal
    lowPrice: Decimal
    volume: int
    turnover: Decimal
    changePct: Decimal | None = None
    createdAt: datetime

    class Config:
        from_attributes = True


class DailyQuoteListResponse(BaseModel):
    stockCode: str
    total: int
    items: list[DailyQuoteResponse]
