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
    expma5: Decimal | None = None
    expma13: Decimal | None = None
    expma34: Decimal | None = None
    expma89: Decimal | None = None
    macdDiff: Decimal | None = None
    macdDea: Decimal | None = None
    macdBar: Decimal | None = None
    createdAt: datetime

    class Config:
        from_attributes = True


class DailyQuoteListResponse(BaseModel):
    stockCode: str
    total: int
    items: list[DailyQuoteResponse]
