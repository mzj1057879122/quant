from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.backtest_result import BacktestResult

router = APIRouter(prefix="/backtest", tags=["回测结果"])


@router.get("/stats")
def getStats(
    version: str | None = Query(None, description="v1/v2"),
    db: Session = Depends(getDb),
):
    """统计胜率（按版本、按板块、按置信度）"""
    baseQuery = db.query(BacktestResult).filter(BacktestResult.isCorrect.isnot(None))
    if version:
        baseQuery = baseQuery.filter(BacktestResult.version == version)

    total = baseQuery.count()
    correct = baseQuery.filter(BacktestResult.isCorrect == 1).count()
    overallRate = round(correct / total * 100, 1) if total > 0 else 0

    # 按版本统计
    versionStats = (
        db.query(
            BacktestResult.version,
            func.count(BacktestResult.id).label("total"),
            func.sum(case((BacktestResult.isCorrect == 1, 1), else_=0)).label("correct"),
        )
        .filter(BacktestResult.isCorrect.isnot(None))
        .group_by(BacktestResult.version)
        .all()
    )

    # 按置信度统计
    confidenceStats = (
        db.query(
            BacktestResult.confidence,
            func.count(BacktestResult.id).label("total"),
            func.sum(case((BacktestResult.isCorrect == 1, 1), else_=0)).label("correct"),
        )
        .filter(BacktestResult.isCorrect.isnot(None), BacktestResult.confidence.isnot(None))
        .group_by(BacktestResult.confidence)
        .all()
    )

    return {
        "overall": {"total": total, "correct": correct, "rate": overallRate},
        "byVersion": [
            {
                "version": r.version,
                "total": r.total,
                "correct": r.correct,
                "rate": round(r.correct / r.total * 100, 1) if r.total > 0 else 0,
            }
            for r in versionStats
        ],
        "byConfidence": [
            {
                "confidence": r.confidence,
                "total": r.total,
                "correct": r.correct,
                "rate": round(r.correct / r.total * 100, 1) if r.total > 0 else 0,
            }
            for r in confidenceStats
        ],
    }


@router.get("/list")
def listBacktest(
    stockCode: str | None = Query(None),
    startDate: date | None = Query(None),
    endDate: date | None = Query(None),
    isCorrect: int | None = Query(None, description="1=对 0=错"),
    version: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(getDb),
):
    """预测记录列表（分页，可按股票/日期/对错筛选）"""
    query = db.query(BacktestResult)
    if stockCode:
        query = query.filter(BacktestResult.stockCode == stockCode)
    if startDate:
        query = query.filter(BacktestResult.predictDate >= startDate)
    if endDate:
        query = query.filter(BacktestResult.predictDate <= endDate)
    if isCorrect is not None:
        query = query.filter(BacktestResult.isCorrect == isCorrect)
    if version:
        query = query.filter(BacktestResult.version == version)

    total = query.count()
    items = (
        query.order_by(BacktestResult.predictDate.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "stockCode": r.stockCode,
                "stockName": r.stockName,
                "predictDate": r.predictDate,
                "version": r.version,
                "technicalSignal": r.technicalSignal,
                "newsSignal": r.newsSignal,
                "prediction": r.prediction,
                "confidence": r.confidence,
                "actualResult": r.actualResult,
                "isCorrect": r.isCorrect,
                "actualChangePct": float(r.actualChangePct) if r.actualChangePct else None,
                "createdAt": r.createdAt,
            }
            for r in items
        ],
    }


@router.get("/trend")
def getTrend(
    version: str | None = Query(None),
    db: Session = Depends(getDb),
):
    """胜率趋势（按预测日期聚合）"""
    query = (
        db.query(
            BacktestResult.predictDate,
            func.count(BacktestResult.id).label("total"),
            func.sum(case((BacktestResult.isCorrect == 1, 1), else_=0)).label("correct"),
        )
        .filter(BacktestResult.isCorrect.isnot(None))
    )
    if version:
        query = query.filter(BacktestResult.version == version)

    rows = query.group_by(BacktestResult.predictDate).order_by(BacktestResult.predictDate).all()

    return {
        "items": [
            {
                "date": r.predictDate,
                "total": r.total,
                "correct": r.correct,
                "rate": round(r.correct / r.total * 100, 1) if r.total > 0 else 0,
            }
            for r in rows
        ]
    }


@router.get("/stock/{stockCode}")
def getStockBacktest(stockCode: str, db: Session = Depends(getDb)):
    """单只股票的回测胜率汇总"""
    rows = (
        db.query(BacktestResult)
        .filter(BacktestResult.stockCode == stockCode, BacktestResult.isCorrect.isnot(None))
        .all()
    )
    total = len(rows)
    correct = sum(1 for r in rows if r.isCorrect == 1)
    return {
        "stockCode": stockCode,
        "total": total,
        "correct": correct,
        "rate": round(correct / total * 100, 1) if total > 0 else 0,
    }
