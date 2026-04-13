from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import getDb
from app.schemas.stock import StockListResponse, StockResponse
from app.services import stock_service
from app.services.quote_service import getQuotesByStockCode, getLatestQuote
from app.schemas.daily_quote import DailyQuoteListResponse, DailyQuoteResponse
from datetime import date

router = APIRouter(prefix="/stocks", tags=["股票管理"])


@router.get("", response_model=StockListResponse)
def listStocks(
    keyword: str | None = Query(None, description="搜索关键字"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    tier: str | None = Query(None, description="分级过滤 A/B/C"),
    db: Session = Depends(getDb),
):
    """获取股票列表"""
    items, total = stock_service.getStockList(db, keyword, page, pageSize, tier)
    return StockListResponse(total=total, items=items)


@router.get("/{stockCode}", response_model=StockResponse)
def getStock(stockCode: str, db: Session = Depends(getDb)):
    """获取单只股票详情"""
    stock = stock_service.getStockByCode(db, stockCode)
    if not stock:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="股票不存在")
    return stock


@router.post("/sync")
def syncStocks(db: Session = Depends(getDb)):
    """同步akshare股票列表"""
    count = stock_service.syncStockList(db)
    return {"message": "同步完成", "newCount": count}
