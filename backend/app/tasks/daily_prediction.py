from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.watchlist import Watchlist
from app.models.daily_quote import DailyQuote
from app.models.backtest_result import BacktestResult
from app.models.limit_up_plate import LimitUpPlate
from app.models.strategy_rule import StrategyRule
from app.services import strategy_service
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_daily_prediction")

# 消息面规则定义：(key, value, desc, category)
_MSG_RULES = [
    ("msg_self_limit_up",  2.0,  "个股今日涨停加分", "sector"),
    ("msg_sector_active",  1.0,  "板块今日活跃加分", "sector"),
    ("msg_sector_continue", 1.0, "板块持续活跃加分", "sector"),
    ("msg_sector_retreat", -1.0, "板块今日退潮减分", "sector"),
    ("msg_sector_cold",    -1.0, "板块3日冷寂减分",  "sector"),
]


def _ensureMsgRules(db: Session) -> None:
    """确保消息面规则存在于 strategy_rules 表，不存在则插入"""
    for key, value, desc, category in _MSG_RULES:
        existing = db.execute(
            select(StrategyRule).where(StrategyRule.ruleKey == key)
        ).scalar_one_or_none()
        if existing is None:
            db.add(StrategyRule(
                ruleKey=key,
                ruleValue=Decimal(str(value)),
                ruleDesc=desc,
                category=category,
                isActive=1,
                updatedBy="system",
            ))
    db.commit()


def _getRecentQuotes(db: Session, stockCode: str, days: int) -> list[DailyQuote]:
    """查最近N天日线数据，按交易日升序"""
    rows = (
        db.execute(
            select(DailyQuote)
            .where(DailyQuote.stockCode == stockCode)
            .order_by(DailyQuote.tradeDate.desc())
            .limit(days)
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))


def _calcAvgVolume(quotes: list[DailyQuote], n: int = 5) -> Decimal | None:
    """计算最近N日均量（不含今日）"""
    if len(quotes) < n + 1:
        return None
    recent = quotes[-(n + 1) : -1]
    total = sum(q.volume for q in recent)
    return Decimal(total) / n


def _getPlateNames(db: Session, tradeDate: date) -> set[str]:
    """查某日 limit_up_plate 的所有板块名集合"""
    rows = (
        db.execute(
            select(LimitUpPlate.plateName)
            .where(LimitUpPlate.tradeDate == tradeDate)
            .distinct()
        )
        .scalars()
        .all()
    )
    return set(rows)


def _getMsgScore(db: Session, stock: Watchlist, today: date, rules: dict) -> tuple[int, list[str]]:
    """查消息面信号，返回(分值, 信号列表)"""
    sectors = [s.strip() for s in (stock.sector or "").split("/") if s.strip()]
    msgScore = 0
    msgSignals: list[str] = []

    # 个股今日涨停
    selfLimitUp = db.execute(
        select(LimitUpPlate).where(
            LimitUpPlate.stockCode == stock.stockCode,
            LimitUpPlate.tradeDate == today,
        )
    ).scalar_one_or_none()
    if selfLimitUp:
        msgScore += int(rules["msg_self_limit_up"])
        msgSignals.append("个股今日涨停")

    if not sectors:
        return msgScore, msgSignals

    yesterday = today - timedelta(days=1)
    day2ago = today - timedelta(days=2)

    todayPlates = _getPlateNames(db, today)
    yPlates = _getPlateNames(db, yesterday)
    d2Plates = _getPlateNames(db, day2ago)

    activeToday = any(s in todayPlates for s in sectors)
    activeYday = any(s in yPlates for s in sectors)
    activeD2 = any(s in d2Plates for s in sectors)

    if activeToday:
        msgScore += int(rules["msg_sector_active"])
        matched = [s for s in sectors if s in todayPlates]
        msgSignals.append(f"板块今日活跃：{'、'.join(matched)}")
        if activeYday:
            msgScore += int(rules["msg_sector_continue"])
            msgSignals.append("板块持续活跃（昨日也有）")
    else:
        if activeYday:
            msgScore += int(rules["msg_sector_retreat"])
            msgSignals.append("板块今日退潮（昨日有今日无）")
        if not activeToday and not activeYday and not activeD2:
            msgScore += int(rules["msg_sector_cold"])
            msgSignals.append("板块连续3日冷寂")

    return msgScore, msgSignals


def _predictStock(db: Session, stock: Watchlist, today: date, rules: dict) -> dict | None:
    """对单只股票执行技术+消息面打分，返回预测结果字典"""
    quotes = _getRecentQuotes(db, stock.stockCode, 42)
    if len(quotes) < 22:
        logger.info(f"数据不足跳过 code={stock.stockCode} count={len(quotes)}")
        return None

    todayQ = quotes[-1]
    # 允许最近3个自然日内的数据（兼容周末/节假日）
    from datetime import timedelta
    if (today - todayQ.tradeDate).days > 3:
        logger.info(f"数据过旧跳过 code={stock.stockCode} latestDate={todayQ.tradeDate}")
        return None

    prevQuotes = quotes[:-1]  # 不含今日
    avgVol5 = _calcAvgVolume(quotes, 5)
    breakoutDays = int(rules["breakout_days"])
    high20 = max(q.highPrice for q in prevQuotes[-breakoutDays:]) if len(prevQuotes) >= breakoutDays else None

    signals: list[str] = []
    techScore = 0

    # --- 规则1：启动信号检测 ---
    if avgVol5 and high20:
        volOk = todayQ.volume >= avgVol5 * rules["volume_ratio_min"]
        changePct = todayQ.changePct or Decimal("0")
        gainOk = changePct >= rules["gain_pct_min"]
        breakoutOk = todayQ.closePrice > high20
        if volOk and gainOk and breakoutOk:
            techScore += 1
            signals.append(f"启动信号：放量+涨幅+突破{breakoutDays}日高")

    # --- 规则2：趋势判断（基于锚位）---
    anchorBroken = False
    if stock.anchorPrice:
        anchor = stock.anchorPrice
        if todayQ.closePrice > anchor:
            techScore += 1
            signals.append(f"趋势有效：收盘{todayQ.closePrice}>锚位{anchor}")
        else:
            techScore -= 1
            anchorBroken = True
            signals.append(f"趋势破坏：收盘{todayQ.closePrice}<锚位{anchor}")

    # --- 规则3：量能状态 ---
    if len(prevQuotes) >= 1 and avgVol5:
        yesterdayQ = prevQuotes[-1]
        # 缩量收阳：洗盘加分
        if (
            todayQ.volume < yesterdayQ.volume * rules["shrink_ratio"]
            and todayQ.closePrice > todayQ.openPrice
        ):
            techScore += 1
            signals.append("缩量收阳：洗盘形态")
        # 极值量顶部：减分
        upperShadow = todayQ.highPrice - max(todayQ.openPrice, todayQ.closePrice)
        bodyHigh = max(todayQ.openPrice, todayQ.closePrice)
        upperShadowRatio = upperShadow / bodyHigh if bodyHigh > 0 else Decimal("0")
        if (
            todayQ.volume > avgVol5 * rules["extreme_vol_ratio"]
            and todayQ.closePrice < todayQ.openPrice
            and upperShadowRatio >= Decimal("0.02")
        ):
            techScore -= 1
            signals.append("极值量收阴+长上影：顶部风险")

    # --- 消息面信号 ---
    msgScore, msgSignals = _getMsgScore(db, stock, today, rules)
    signals.extend(msgSignals)

    # --- 综合预测（分值驱动）---
    totalScore = techScore + msgScore

    if anchorBroken:
        prediction = "看空"
        if totalScore <= -2:
            confidence = "高"
        elif totalScore <= -1:
            confidence = "中"
        else:
            confidence = "低"
    elif totalScore >= 4:
        prediction = "看多"
        confidence = "高"
    elif totalScore >= 2:
        prediction = "看多"
        confidence = "中"
    elif totalScore >= 1:
        prediction = "看多"
        confidence = "低"
    else:
        prediction = "中性"
        confidence = "低"

    return {
        "stockCode": stock.stockCode,
        "stockName": stock.stockName,
        "predictDate": today,
        "version": "v3_auto",
        "technicalSignal": "；".join(signals) if signals else "无明显信号",
        "prediction": prediction,
        "confidence": confidence,
    }


def runDailyPrediction() -> None:
    """定时任务：每日收盘后对 watchlist 中 status=watching 的股票打分"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        _ensureMsgRules(db)

        stocks = (
            db.execute(select(Watchlist).where(Watchlist.status == "watching"))
            .scalars()
            .all()
        )
        if not stocks:
            logger.info("watchlist 无 watching 股票，跳过预测")
            return

        rules = strategy_service.getRules(db)

        saved = 0
        for stock in stocks:
            try:
                result = _predictStock(db, stock, today, rules)
                if result is None:
                    continue

                # 去重：同一股票同一日期只保留一条（upsert 用 delete+insert）
                existing = db.execute(
                    select(BacktestResult).where(
                        BacktestResult.stockCode == result["stockCode"],
                        BacktestResult.predictDate == result["predictDate"],
                        BacktestResult.version == result["version"],
                    )
                ).scalar_one_or_none()
                if existing:
                    db.delete(existing)
                    db.flush()

                record = BacktestResult(
                    stockCode=result["stockCode"],
                    stockName=result["stockName"],
                    predictDate=result["predictDate"],
                    version=result["version"],
                    technicalSignal=result["technicalSignal"],
                    prediction=result["prediction"],
                    confidence=result["confidence"],
                )
                db.add(record)
                saved += 1
            except Exception as e:
                logger.error(f"股票预测异常 code={stock.stockCode} 错误={e}", exc_info=True)

        db.commit()
        logger.info(f"每日预测完成 total={len(stocks)} saved={saved}")
    except Exception as e:
        db.rollback()
        logger.error(f"每日预测任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
