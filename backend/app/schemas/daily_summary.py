from datetime import date, datetime

from pydantic import BaseModel


class DailySummaryResponse(BaseModel):
    id: int
    summaryDate: date
    articleCount: int
    consensus: str | None = None
    divergence: str | None = None
    stockViews: str | None = None
    sectorViews: str | None = None
    strategy: str | None = None
    evolution: str | None = None
    status: str
    errorMessage: str | None = None
    processDuration: int | None = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class DailySummaryListResponse(BaseModel):
    total: int
    items: list[DailySummaryResponse]


class DailySummaryStatusResponse(BaseModel):
    id: int
    summaryDate: date
    status: str
    errorMessage: str | None = None
    processDuration: int | None = None

    class Config:
        from_attributes = True
