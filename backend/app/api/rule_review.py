from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.database import getDb
from app.models.rule_review import RuleReview

router = APIRouter(prefix="/rule-review", tags=["规则复盘"])


@router.get("/latest")
def getLatest(db: Session = Depends(getDb)):
    """最新一条规则复盘结论"""
    record = db.execute(
        select(RuleReview).order_by(desc(RuleReview.reviewDate)).limit(1)
    ).scalar_one_or_none()
    if not record:
        return {"message": "暂无复盘数据"}
    return _format(record)


@router.get("/list")
def listReviews(
    days: int = Query(30, description="最近N天"),
    db: Session = Depends(getDb),
):
    """规则复盘历史列表"""
    from datetime import timedelta
    since = date.today() - timedelta(days=days)
    rows = db.execute(
        select(RuleReview)
        .where(RuleReview.reviewDate >= since)
        .order_by(desc(RuleReview.reviewDate))
    ).scalars().all()
    return {"items": [_format(r) for r in rows]}


def _format(r: RuleReview) -> dict:
    import json
    return {
        "reviewDate": r.reviewDate,
        "windowDays": r.windowDays,
        "totalPredictions": r.totalPredictions,
        "overallWinRate": float(r.overallWinRate) if r.overallWinRate else None,
        "bySignalType": json.loads(r.bySignalType) if r.bySignalType else None,
        "byConfidence": json.loads(r.byConfidence) if r.byConfidence else None,
        "byPrediction": json.loads(r.byPrediction) if r.byPrediction else None,
        "anomalies": r.anomalies,
        "suggestions": r.suggestions,
        "alertLevel": r.alertLevel,
        "createdAt": r.createdAt,
    }
