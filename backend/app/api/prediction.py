from datetime import date as DateType
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.backtest_result import BacktestResult

router = APIRouter(prefix="/prediction", tags=["持仓预测"])

CONFIDENCE_ORDER = {"高": 0, "中": 1, "低": 2}
PREDICTION_ORDER = {"看多": 0, "看空": 1, "中性": 2}


@router.get("/daily")
def getDailyPrediction(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认取最近有数据的日期"),
    db: Session = Depends(getDb),
):
    """查询指定日期的 v4_auto 预测结果，自动回退到最近有数据的日期"""
    if date:
        target_date = DateType.fromisoformat(date)
        # 指定日期无数据时，回退到最近有 v4_auto 数据的日期
        count = db.query(func.count(BacktestResult.id)).filter(
            BacktestResult.predictDate == target_date,
            BacktestResult.version == "v4_auto",
        ).scalar()
        if not count:
            latest = (
                db.query(func.max(BacktestResult.predictDate))
                .filter(BacktestResult.version == "v4_auto")
                .scalar()
            )
            target_date = latest if latest else target_date
    else:
        latest = (
            db.query(func.max(BacktestResult.predictDate))
            .filter(BacktestResult.version == "v4_auto")
            .scalar()
        )
        target_date = latest if latest else DateType.today()

    rows = (
        db.query(BacktestResult)
        .filter(
            BacktestResult.predictDate == target_date,
            BacktestResult.version == "v4_auto",
        )
        .all()
    )

    bullish = 0
    bearish = 0
    neutral = 0
    items = []

    for br in rows:
        prediction = br.prediction or "中性"
        if prediction == "看多":
            bullish += 1
        elif prediction == "看空":
            bearish += 1
        else:
            neutral += 1

        actualChangePct = float(br.actualChangePct) if br.actualChangePct is not None else None

        items.append({
            "stockCode": br.stockCode,
            "stockName": br.stockName,
            "prediction": prediction,
            "confidence": br.confidence,
            "actualChangePct": actualChangePct,
            "isCorrect": br.isCorrect,
        })

    # 排序：看多 > 看空 > 中性，同类内置信度 高 > 中 > 低
    items.sort(key=lambda x: (
        PREDICTION_ORDER.get(x["prediction"], 9),
        CONFIDENCE_ORDER.get(x["confidence"] or "", 9),
    ))

    return {
        "date": target_date.isoformat(),
        "items": items,
        "summary": {"bullish": bullish, "bearish": bearish, "neutral": neutral},
    }
