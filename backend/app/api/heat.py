from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import getDb
from app.services import heat_service

router = APIRouter(prefix="/heat", tags=["股票热度"])


@router.get("/top")
def getHeatTop(
    heatDate: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(getDb),
):
    """热度排行榜 TOP N"""
    items = heat_service.getHeatTop(db, heatDate, limit)
    return {"items": items, "total": len(items)}


@router.get("/{stockCode}")
def getStockHeatDetail(
    stockCode: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(getDb),
):
    """单只股票热度历史"""
    items = heat_service.getStockHeatDetail(db, stockCode, limit)
    return {"items": items, "total": len(items)}
