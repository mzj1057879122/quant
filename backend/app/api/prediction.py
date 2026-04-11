from datetime import date as DateType
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.backtest_result import BacktestResult
from app.models.daily_quote import DailyQuote
from app.models.watchlist import Watchlist

router = APIRouter(prefix="/prediction", tags=["持仓预测"])


@router.get("/daily")
def getDailyPrediction(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    db: Session = Depends(getDb),
):
    """查询指定日期的 v3_auto 预测结果，关联 watchlist 锚位信息和最新收盘价"""
    target_date = DateType.fromisoformat(date) if date else DateType.today()

    rows = (
        db.query(BacktestResult, Watchlist)
        .outerjoin(Watchlist, Watchlist.stockCode == BacktestResult.stockCode)
        .filter(
            BacktestResult.predictDate == target_date,
            BacktestResult.version == "v3_auto",
        )
        .all()
    )

    # 批量查各股最新行情（不依赖日期，避免周末无数据）
    stockCodes = [br.stockCode for br, _ in rows]
    latestQuoteMap: dict = {}
    if stockCodes:
        subq = (
            db.query(DailyQuote.stockCode, func.max(DailyQuote.tradeDate).label("maxDate"))
            .filter(DailyQuote.stockCode.in_(stockCodes))
            .group_by(DailyQuote.stockCode)
            .subquery()
        )
        latestQuotes = (
            db.query(DailyQuote)
            .join(subq, (DailyQuote.stockCode == subq.c.stockCode) & (DailyQuote.tradeDate == subq.c.maxDate))
            .all()
        )
        for dq in latestQuotes:
            latestQuoteMap[dq.stockCode] = dq

    items = []
    bullish = 0
    bearish = 0
    neutral = 0

    for br, wl in rows:
        dq = latestQuoteMap.get(br.stockCode)
        latestClose = float(dq.closePrice) if dq else None
        latestDate = dq.tradeDate.isoformat() if dq else None
        anchorPrice = float(wl.anchorPrice) if wl and wl.anchorPrice else None

        changeFromAnchor = None
        if latestClose is not None and anchorPrice:
            changeFromAnchor = round((latestClose - anchorPrice) / anchorPrice * 100, 2)

        prediction = br.prediction or "中性"
        if prediction == "看多":
            bullish += 1
        elif prediction == "看空":
            bearish += 1
        else:
            neutral += 1

        items.append({
            "stockCode": br.stockCode,
            "stockName": br.stockName,
            "sector": wl.sector if wl else None,
            "prediction": prediction,
            "confidence": br.confidence,
            "technicalSignal": br.technicalSignal,
            "anchorPrice": anchorPrice,
            "latestClose": latestClose,
            "latestDate": latestDate,
            "changeFromAnchor": changeFromAnchor,
            "anchorDate": wl.anchorDate.isoformat() if wl and wl.anchorDate else None,
            "status": wl.status if wl else None,
        })

    return {
        "date": target_date.isoformat(),
        "items": items,
        "summary": {"bullish": bullish, "bearish": bearish, "neutral": neutral},
    }
