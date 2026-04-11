from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.strategy_rule import StrategyRule
from app.utils.logger import setupLogger

logger = setupLogger("strategy_service")

# 兜底默认值，数据库不可用时使用
_DEFAULTS: dict[str, float] = {
    "volume_ratio_min": 1.8,
    "gain_pct_min": 5.0,
    "breakout_days": 20,
    "anchor_break_pct": 0.0,
    "shrink_ratio": 0.5,
    "extreme_vol_ratio": 3.0,
    "conf_high_signals": 2,
    "conf_mid_signals": 1,
    "sector_retreat_days": 2,
    "dynamic_anchor_vol": 1.8,
}


def getRules(db: Session) -> dict[str, Decimal]:
    """从 strategy_rules 表读取所有活跃规则，返回 {key: value} dict"""
    rows = (
        db.execute(select(StrategyRule).where(StrategyRule.isActive == 1))
        .scalars()
        .all()
    )
    result = {k: Decimal(str(v)) for k, v in _DEFAULTS.items()}
    for row in rows:
        result[row.ruleKey] = row.ruleValue
    return result


def updateRule(db: Session, key: str, value: float, updated_by: str = "xiaozhua") -> StrategyRule:
    """更新单条规则，不存在时抛 ValueError"""
    rule = db.execute(
        select(StrategyRule).where(StrategyRule.ruleKey == key)
    ).scalar_one_or_none()
    if rule is None:
        raise ValueError(f"规则不存在: {key}")
    rule.ruleValue = Decimal(str(value))
    rule.updatedBy = updated_by
    db.commit()
    db.refresh(rule)
    logger.info(f"规则更新 key={key} value={value} by={updated_by}")
    return rule
