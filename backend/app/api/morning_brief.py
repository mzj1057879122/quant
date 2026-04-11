from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.morning_brief import MorningBrief

router = APIRouter(prefix="/brief", tags=["盘前纪要"])


@router.get("/latest")
def getLatestBrief(
    source: str | None = Query(None, description="briefA/briefB"),
    db: Session = Depends(getDb),
):
    """最新一条盘前纪要"""
    query = db.query(MorningBrief)
    if source:
        query = query.filter(MorningBrief.source == source)
    brief = query.order_by(MorningBrief.briefDate.desc()).first()
    if not brief:
        return {"brief": None}
    return {
        "brief": {
            "id": brief.id,
            "briefDate": brief.briefDate,
            "source": brief.source,
            "rawContent": brief.rawContent,
            "aiSummary": brief.aiSummary,
            "hotSectors": brief.hotSectors,
            "createdAt": brief.createdAt,
        }
    }


@router.get("/list")
def listBriefs(
    source: str | None = Query(None),
    startDate: date | None = Query(None),
    endDate: date | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(getDb),
):
    """盘前纪要列表（分页）"""
    query = db.query(MorningBrief)
    if source:
        query = query.filter(MorningBrief.source == source)
    if startDate:
        query = query.filter(MorningBrief.briefDate >= startDate)
    if endDate:
        query = query.filter(MorningBrief.briefDate <= endDate)

    total = query.count()
    items = (
        query.order_by(MorningBrief.briefDate.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": b.id,
                "briefDate": b.briefDate,
                "source": b.source,
                "aiSummary": b.aiSummary,
                "hotSectors": b.hotSectors,
                "createdAt": b.createdAt,
            }
            for b in items
        ],
    }


@router.get("/{briefDate}")
def getBriefByDate(briefDate: date, db: Session = Depends(getDb)):
    """获取指定日期的所有盘前纪要"""
    briefs = (
        db.query(MorningBrief)
        .filter(MorningBrief.briefDate == briefDate)
        .order_by(MorningBrief.source)
        .all()
    )
    return {
        "items": [
            {
                "id": b.id,
                "briefDate": b.briefDate,
                "source": b.source,
                "rawContent": b.rawContent,
                "aiSummary": b.aiSummary,
                "hotSectors": b.hotSectors,
                "createdAt": b.createdAt,
            }
            for b in briefs
        ]
    }
