import json
from datetime import date, datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.watchlist import Watchlist
from app.models.user_config import UserConfig
from app.services.config_service import getConfig, setConfig
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
    anchorDistPct: float | None
    tier: str | None = None
    sortOrder: int = 0
    sectorColor: str | None = None
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


class SectorUpdateRequest(BaseModel):
    sector: str


class ReorderItem(BaseModel):
    stockCode: str
    sortOrder: int


class SectorColorRequest(BaseModel):
    sector: str
    color: str


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
        "tier": w.tier,
        "sortOrder": w.sortOrder if w.sortOrder is not None else 0,
        "sectorColor": w.sectorColor,
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
    items = query.order_by(Watchlist.sortOrder.asc(), Watchlist.id.asc()).all()

    result = []
    for w in items:
        latestQuote = getLatestQuote(db, w.stockCode)
        latestPrice = float(latestQuote.closePrice) if latestQuote and latestQuote.closePrice else None
        result.append(_buildItem(w, latestPrice))

    return {"items": result, "total": len(result)}


@router.get("/items")
def listWatchlistItems(
    status: str | None = Query(None, description="watching/holding/exited"),
    db: Session = Depends(getDb),
):
    """获取全部自选股（新版，含 sortOrder/sectorColor）"""
    return listWatchlist(status=status, db=db)


@router.post("/add")
def addWatchlist(req: WatchlistAddRequest, db: Session = Depends(getDb)):
    """添加股票到自选股池"""
    existing = db.query(Watchlist).filter(Watchlist.stockCode == req.stockCode).first()
    if existing:
        raise HTTPException(status_code=400, detail="股票已在自选股池中")

    # 新加的股票 sortOrder 设为当前最大值+1
    maxOrder = db.query(Watchlist).count()

    w = Watchlist(
        stockCode=req.stockCode,
        stockName=req.stockName,
        sector=req.sector,
        addReason=req.addReason,
        status=req.status,
        anchorPrice=Decimal(str(req.anchorPrice)) if req.anchorPrice else None,
        anchorDate=req.anchorDate,
        confidence=req.confidence,
        sortOrder=maxOrder,
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


@router.patch("/items/{stockCode}/sector")
def updateSector(stockCode: str, req: SectorUpdateRequest, db: Session = Depends(getDb)):
    """只更新板块字段"""
    w = db.query(Watchlist).filter(Watchlist.stockCode == stockCode).first()
    if not w:
        raise HTTPException(status_code=404, detail="股票不在自选股池中")
    w.sector = req.sector
    db.commit()
    return {"message": "板块已更新"}


@router.post("/reorder")
def reorderWatchlist(items: List[ReorderItem], db: Session = Depends(getDb)):
    """批量更新排序"""
    for item in items:
        w = db.query(Watchlist).filter(Watchlist.stockCode == item.stockCode).first()
        if w:
            w.sortOrder = item.sortOrder
    db.commit()
    return {"message": "排序已保存"}


@router.get("/sector-colors")
def getSectorColors(db: Session = Depends(getDb)):
    """获取所有板块颜色配置"""
    raw = getConfig(db, "sector_colors")
    if raw:
        try:
            colors = json.loads(raw)
        except Exception:
            colors = {}
    else:
        colors = {}
    return {"colors": colors}


@router.post("/sector-colors")
def saveSectorColor(req: SectorColorRequest, db: Session = Depends(getDb)):
    """保存板块颜色（合并更新）"""
    raw = getConfig(db, "sector_colors")
    if raw:
        try:
            colors = json.loads(raw)
        except Exception:
            colors = {}
    else:
        colors = {}
    colors[req.sector] = req.color
    setConfig(db, "sector_colors", json.dumps(colors, ensure_ascii=False))
    return {"message": "颜色已保存"}


@router.delete("/{code}")
def deleteWatchlist(code: str, db: Session = Depends(getDb)):
    """从自选股池移除"""
    w = db.query(Watchlist).filter(Watchlist.stockCode == code).first()
    if not w:
        raise HTTPException(status_code=404, detail="股票不在自选股池中")
    db.delete(w)
    db.commit()
    return {"message": "已移除"}
