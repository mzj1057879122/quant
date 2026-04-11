from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.watchlist import Watchlist
from app.models.daily_quote import DailyQuote
from app.models.backtest_result import BacktestResult
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_daily_prediction")


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


def _predictStock(db: Session, stock: Watchlist, today: date) -> dict | None:
    """对单只股票执行技术打分，返回预测结果字典"""
    quotes = _getRecentQuotes(db, stock.stockCode, 42)
    if len(quotes) < 22:
        logger.info(f"数据不足跳过 code={stock.stockCode} count={len(quotes)}")
        return None

    todayQ = quotes[-1]
    if todayQ.tradeDate != today:
        logger.info(f"今日数据缺失跳过 code={stock.stockCode} latestDate={todayQ.tradeDate}")
        return None

    prevQuotes = quotes[:-1]  # 不含今日
    avgVol5 = _calcAvgVolume(quotes, 5)
    high20 = max(q.highPrice for q in prevQuotes[-20:]) if len(prevQuotes) >= 20 else None

    signals: list[str] = []
    positiveCount = 0
    negativeCount = 0

    # --- 规则1：启动信号检测 ---
    launchSignal = False
    if avgVol5 and high20:
        volOk = todayQ.volume >= avgVol5 * Decimal("1.8")
        changePct = todayQ.changePct or Decimal("0")
        gainOk = changePct >= Decimal("5")
        breakoutOk = todayQ.closePrice > high20
        if volOk and gainOk and breakoutOk:
            launchSignal = True
            signals.append("启动信号：放量+涨幅+突破20日高")
            positiveCount += 1

    # --- 规则2：趋势判断（基于锚位）---
    if stock.anchorPrice:
        anchor = stock.anchorPrice
        if todayQ.closePrice > anchor:
            signals.append(f"趋势有效：收盘{todayQ.closePrice}>锚位{anchor}")
            positiveCount += 1
        else:
            signals.append(f"趋势破坏：收盘{todayQ.closePrice}<锚位{anchor}")
            negativeCount += 1

    # --- 规则3：量能状态 ---
    if len(prevQuotes) >= 1 and avgVol5:
        yesterdayQ = prevQuotes[-1]
        # 缩量收阳：洗盘加分
        if (
            todayQ.volume < yesterdayQ.volume * Decimal("0.5")
            and todayQ.closePrice > todayQ.openPrice
        ):
            signals.append("缩量收阳：洗盘形态")
            positiveCount += 1
        # 极值量顶部：减分
        upperShadow = todayQ.highPrice - max(todayQ.openPrice, todayQ.closePrice)
        bodyHigh = max(todayQ.openPrice, todayQ.closePrice)
        upperShadowRatio = upperShadow / bodyHigh if bodyHigh > 0 else Decimal("0")
        if (
            todayQ.volume > avgVol5 * 3
            and todayQ.closePrice < todayQ.openPrice
            and upperShadowRatio >= Decimal("0.02")
        ):
            signals.append("极值量收阴+长上影：顶部风险")
            negativeCount += 1

    # --- 综合预测 ---
    if positiveCount >= 1 and negativeCount == 0:
        prediction = "看多"
    elif negativeCount >= 1 and positiveCount == 0:
        prediction = "看空"
    elif positiveCount > negativeCount:
        prediction = "看多"
    elif negativeCount > positiveCount:
        prediction = "看空"
    else:
        prediction = "中性"

    totalSignals = positiveCount + negativeCount
    if positiveCount >= 2 or negativeCount >= 2:
        confidence = "高"
    elif totalSignals >= 1:
        confidence = "中"
    else:
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
        stocks = (
            db.execute(select(Watchlist).where(Watchlist.status == "watching"))
            .scalars()
            .all()
        )
        if not stocks:
            logger.info("watchlist 无 watching 股票，跳过预测")
            return

        saved = 0
        for stock in stocks:
            try:
                result = _predictStock(db, stock, today)
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
