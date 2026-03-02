from datetime import datetime

from pydantic import BaseModel


class StockBase(BaseModel):
    stockCode: str
    stockName: str
    market: str
    industry: str | None = None


class StockCreate(StockBase):
    pass


class StockResponse(StockBase):
    id: int
    isActive: int
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class StockListResponse(BaseModel):
    total: int
    items: list[StockResponse]
