from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class SignalResponse(BaseModel):
    id: int
    stockCode: str
    stockName: str
    signalType: str
    signalDate: date
    previousHighId: int | None = None
    previousHighPrice: Decimal
    triggerPrice: Decimal
    closePrice: Decimal
    successRate: Decimal | None = None
    description: str | None = None
    isNotified: int
    isRead: int
    createdAt: datetime

    class Config:
        from_attributes = True


class SignalListResponse(BaseModel):
    total: int
    items: list[SignalResponse]


class SignalUnreadResponse(BaseModel):
    count: int


class SignalStatItem(BaseModel):
    signalType: str
    count: int


class SignalStatResponse(BaseModel):
    items: list[SignalStatItem]


class CurrentHighInfo(BaseModel):
    highPrice: float | None = None
    highDate: str | None = None
    status: str | None = None


class AnalysisSummary(BaseModel):
    totalApproachCount: int = 0
    breakoutSuccessCount: int = 0
    breakoutFailCount: int = 0
    successRate: float = 0


class HistoryEvent(BaseModel):
    eventDate: str
    highPrice: float
    approachPrice: float
    result: str
    maxGainPct: float = 0
    maxDropPct: float = 0
    daysToResult: int = 0


class BreakoutAnalysisResponse(BaseModel):
    stockCode: str
    stockName: str
    currentHigh: CurrentHighInfo | None = None
    analysis: AnalysisSummary
    historyEvents: list[HistoryEvent] = []
    currentStatus: str = "none"
    latestClose: float | None = None
