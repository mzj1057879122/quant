from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import getDb
from app.services import strategy_service
from app.utils.logger import setupLogger

router = APIRouter(prefix="/strategy", tags=["策略规则"])

logger = setupLogger("api_strategy")


class RuleUpdate(BaseModel):
    value: float
    updatedBy: str = "xiaozhua"


@router.get("/rules")
def getAllRules(db: Session = Depends(getDb)):
    """查看所有活跃规则"""
    from sqlalchemy import select
    from app.models.strategy_rule import StrategyRule

    rows = db.execute(select(StrategyRule).order_by(StrategyRule.category, StrategyRule.ruleKey)).scalars().all()
    items = [
        {
            "ruleKey": r.ruleKey,
            "ruleValue": float(r.ruleValue),
            "ruleDesc": r.ruleDesc,
            "category": r.category,
            "isActive": r.isActive,
            "updatedBy": r.updatedBy,
            "updatedAt": r.updatedAt,
        }
        for r in rows
    ]
    return {"items": items}


@router.put("/rules/{key}")
def updateRule(key: str, body: RuleUpdate, db: Session = Depends(getDb)):
    """更新规则值"""
    try:
        rule = strategy_service.updateRule(db, key, body.value, body.updatedBy)
        return {"message": "更新成功", "ruleKey": rule.ruleKey, "ruleValue": float(rule.ruleValue)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
