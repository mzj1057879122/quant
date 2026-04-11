from datetime import date, datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.watchlist import Watchlist
from app.services.quote_service import getLatestQuote

router = APIRouter(prefix="/watchlist", tags=["自选股池"])


class WatchlistItem(BaseModel):
    id: int
    stockCode: str
    stockName: str
    sector: str | None
    addReason: str | None
    status: str
    anchorPrice: float | None
    anchorDate: date | None
    confidence: str | None
    latestPrice: float | None
    anchorDistPct: float | None  # 距锚位%
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class WatchlistAddRequest(BaseModel):
    stockCode: str
    stockName: str
    sector: str | None = None
    addReason: str | None = None
    status: str = "watching"
    anchorPrice: float | None = None
    anchorDate: date | None = None
    confidence: str | None = None


class WatchlistUpdateRequest(BaseModel):
    stockName: str | None = None
    sector: str | None = None
    addReason: str | None = None
    status: str | None = None
    anchorPrice: float | None = None
    anchorDate: date | None = None
    confidence: str | None = None


def _buildItem(w: Watchlist, latestPrice: float | None) -> dict:
    anchorDistPct = None
    if latestPrice and w.anchorPrice:
        anchorDistPct = round((latestPrice - float(w.anchorPrice)) / float(w.anchorPrice) * 100, 2)
    return {
        "id": w.id,
        "stockCode": w.stockCode,
        "stockName": w.stockName,
        "sector": w.sector,
        "addReason": w.addReason,
        "status": w.status,
        "anchorPrice": float(w.anchorPrice) if w.anchorPrice else None,
        "anchorDate": w.anchorDate,
        "confidence": w.confidence,
        "latestPrice": latestPrice,
        "anchorDistPct": anchorDistPct,
        "createdAt": w.createdAt,
        "updatedAt": w.updatedAt,
    }


@router.get("/list")
def listWatchlist(
    status: str | None = Query(None, description="watching/holding/exited"),
    db: Session = Depends(getDb),
):
    """获取全部自选股（带最新行情、锚位距离%）"""
    query = db.query(Watchlist)
    if status:
        query = query.filter(Watchlist.status == status)
    items = query.order_by(Watchlist.createdAt.desc()).all()

    result = []
    for w in items:
        latestQuote = getLatestQuote(db, w.stockCode)
        latestPrice = float(latestQuote.closePrice) if latestQuote and latestQuote.closePrice else None
        result.append(_buildItem(w, latestPrice))

    return {"items": result, "total": len(result)}


@router.post("/add")
def addWatchlist(req: WatchlistAddRequest, db: Session = Depends(getDb)):
    """添加股票到自选股池"""
    existing = db.query(Watchlist).filter(Watchlist.stockCode == req.stockCode).first()
    if existing:
        raise HTTPException(status_code=400, detail="股票已在自选股池中")

    w = Watchlist(
        stockCode=req.stockCode,
        stockName=req.stockName,
        sector=req.sector,
        addReason=req.addReason,
        status=req.status,
        anchorPrice=Decimal(str(req.anchorPrice)) if req.anchorPrice else None,
        anchorDate=req.anchorDate,
        confidence=req.confidence,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"message": "添加成功", "id": w.id}


@router.put("/{code}")
def updateWatchlist(code: str, req: WatchlistUpdateRequest, db: Session = Depends(getDb)):
    """更新自选股状态/锚位等信息"""
    w = db.query(Watchlist).filter(Watchlist.stockCode == code).first()
    if not w:
        raise HTTPException(status_code=404, detail="股票不在自选股池中")

    if req.stockName is not None:
        w.stockName = req.stockName
    if req.sector is not None:
        w.sector = req.sector
    if req.addReason is not None:
        w.addReason = req.addReason
    if req.status is not None:
        w.status = req.status
    if req.anchorPrice is not None:
        w.anchorPrice = Decimal(str(req.anchorPrice))
    if req.anchorDate is not None:
        w.anchorDate = req.anchorDate
    if req.confidence is not None:
        w.confidence = req.confidence

    db.commit()
    return {"message": "更新成功"}


@router.delete("/{code}")
def deleteWatchlist(code: str, db: Session = Depends(getDb)):
    """从自选股池移除"""
    w = db.query(Watchlist).filter(Watchlist.stockCode == code).first()
    if not w:
        raise HTTPException(status_code=404, detail="股票不在自选股池中")
    db.delete(w)
    db.commit()
    return {"message": "已移除"}
