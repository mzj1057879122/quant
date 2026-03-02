from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import getDb
from app.schemas.signal import (
    SignalListResponse, SignalUnreadResponse, SignalStatResponse,
    BreakoutAnalysisResponse,
)
from app.services import signal_service
from app.services.config_service import getWatchList, getDetectionParams
from app.services.detection_service import runFullDetection, getBreakoutAnalysis
from app.models.previous_high import PreviousHigh

router = APIRouter(prefix="/signals", tags=["信号提醒"])


@router.get("", response_model=SignalListResponse)
def listSignals(
    stockCode: str | None = Query(None),
    signalType: str | None = Query(None),
    startDate: date | None = Query(None),
    endDate: date | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(getDb),
):
    """获取信号列表"""
    items, total = signal_service.getSignalList(
        db, stockCode, signalType, startDate, endDate, page, pageSize
    )
    return SignalListResponse(total=total, items=items)


@router.get("/unread", response_model=SignalUnreadResponse)
def getUnread(db: Session = Depends(getDb)):
    """获取未读信号数量"""
    count = signal_service.getUnreadCount(db)
    return SignalUnreadResponse(count=count)


@router.get("/statistics", response_model=SignalStatResponse)
def getStatistics(
    signalDate: date | None = Query(None),
    db: Session = Depends(getDb),
):
    """信号统计"""
    items = signal_service.getSignalStatistics(db, signalDate)
    return SignalStatResponse(items=items)


@router.get("/breakout-analysis/{stockCode}", response_model=BreakoutAnalysisResponse)
def breakoutAnalysis(stockCode: str, db: Session = Depends(getDb)):
    """获取某只股票的突破分析数据"""
    result = getBreakoutAnalysis(db, stockCode)
    if not result:
        raise HTTPException(status_code=404, detail="未找到该股票或无分析数据")
    return result


@router.put("/{signalId}/read")
def markRead(signalId: int, db: Session = Depends(getDb)):
    """标记信号为已读"""
    success = signal_service.markAsRead(db, signalId)
    if not success:
        raise HTTPException(status_code=404, detail="信号不存在")
    return {"message": "已标记为已读"}


@router.put("/read-all")
def markAllRead(db: Session = Depends(getDb)):
    """全部标为已读"""
    count = signal_service.markAllAsRead(db)
    return {"message": "全部已读", "count": count}


@router.get("/previous-highs/{stockCode}")
def getPreviousHighs(stockCode: str, db: Session = Depends(getDb)):
    """获取某只股票的前高记录"""
    items = (
        db.query(PreviousHigh)
        .filter(PreviousHigh.stockCode == stockCode)
        .order_by(PreviousHigh.highDate.desc())
        .all()
    )
    return {"stockCode": stockCode, "total": len(items), "items": items}


@router.post("/detect")
def detectSignals(db: Session = Depends(getDb)):
    """手动触发前高检测"""
    watchList = getWatchList(db)
    if not watchList:
        return {"message": "关注列表为空"}
    params = getDetectionParams(db)
    result = runFullDetection(db, watchList, params)
    return {"message": "检测完成", "result": result}
