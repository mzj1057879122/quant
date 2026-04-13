from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import getDb
from app.schemas.daily_quote import DailyQuoteListResponse
from app.services import quote_service
from app.services.config_service import getWatchList

router = APIRouter(prefix="/quotes", tags=["行情数据"])


@router.get("/{stockCode}", response_model=DailyQuoteListResponse)
def getQuotes(
    stockCode: str,
    startDate: date | None = Query(None, description="起始日期"),
    endDate: date | None = Query(None, description="结束日期"),
    limit: int = Query(250, ge=1, le=1000),
    db: Session = Depends(getDb),
):
    """获取某只股票日线数据"""
    items = quote_service.getQuotesByStockCode(db, stockCode, startDate, endDate, limit)
    return DailyQuoteListResponse(stockCode=stockCode, total=len(items), items=items)


@router.get("/{stockCode}/latest")
def getLatest(stockCode: str, db: Session = Depends(getDb)):
    """获取最新一条行情（含股票名称）"""
    quote = quote_service.getLatestQuote(db, stockCode)
    if not quote:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="暂无行情数据")
    # 补充股票名称
    from app.services.stock_service import getStockByCode
    stock = getStockByCode(db, stockCode)
    return {
        "stockCode": quote.stockCode,
        "stockName": stock.stockName if stock else "--",
        "tradeDate": quote.tradeDate,
        "openPrice": quote.openPrice,
        "closePrice": quote.closePrice,
        "highPrice": quote.highPrice,
        "lowPrice": quote.lowPrice,
        "volume": quote.volume,
        "turnover": quote.turnover,
        "changePct": quote.changePct,
    }


@router.get("/{stockCode}/weekly")
def getWeeklyQuotes(
    stockCode: str,
    limit: int = Query(52, ge=1, le=260),
    db: Session = Depends(getDb),
):
    """获取某只股票最近N周的周线数据（含EXPMA5/13/34）"""
    items = quote_service.getWeeklyQuotes(db, stockCode, limit)
    result = []
    for w in items:
        result.append({
            "stockCode": w.stockCode,
            "weekStart": w.weekStart,
            "openPrice": w.openPrice,
            "closePrice": w.closePrice,
            "highPrice": w.highPrice,
            "lowPrice": w.lowPrice,
            "volume": w.volume,
            "expma5": w.expma5,
            "expma13": w.expma13,
            "expma34": w.expma34,
        })
    return {"stockCode": stockCode, "total": len(result), "items": result}


@router.post("/fetch")
def fetchQuotes(
    stockCode: str | None = Query(None, description="指定股票代码，为空则拉取全部关注"),
    db: Session = Depends(getDb),
):
    """手动触发拉取行情"""
    if stockCode:
        count = quote_service.fetchDailyQuotes(db, stockCode)
        return {"message": "拉取完成", "stockCode": stockCode, "count": count}
    else:
        watchList = getWatchList(db)
        if not watchList:
            return {"message": "关注列表为空"}
        result = quote_service.fetchAllWatchListQuotes(db, watchList)
        return {"message": "批量拉取完成", "result": result}
