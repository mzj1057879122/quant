import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.breakout_analysis import BreakoutAnalysis
from app.models.daily_quote import DailyQuote
from app.models.previous_high import PreviousHigh
from app.models.signal import Signal
from app.models.stock import Stock
from app.utils.logger import setupLogger

logger = setupLogger("detection_service")

# 默认检测参数
DEFAULT_PARAMS = {
    "lookbackDays": 250,
    "windowSize": 5,
    "minDropPct": 0.05,
    "approachPct": 0.95,
    "observeDays": 20,
}


def findLatestPreviousHigh(
    db: Session,
    stockCode: str,
    params: dict | None = None,
) -> PreviousHigh | None:
    """
    从最新行情往前扫描，找到最近一个有效前高（阻力位）
    条件：
    1. 在 [i-windowSize, i+windowSize] 窗口内是最大值
    2. 高点之后有明显回撤（回落超 minDropPct）
    3. 高点后面至少有 windowSize 天数据（排除正在上涨的情况）
    """
    if params is None:
        params = DEFAULT_PARAMS

    lookbackDays = params.get("lookbackDays", 250)
    windowSize = params.get("windowSize", 5)
    minDropPct = Decimal(str(params.get("minDropPct", 0.05)))

    try:
        # 获取最近 lookbackDays 天的日线数据（按日期降序取，再转升序）
        quotes = (
            db.query(DailyQuote)
            .filter(DailyQuote.stockCode == stockCode)
            .order_by(DailyQuote.tradeDate.desc())
            .limit(lookbackDays)
            .all()
        )
        quotes.reverse()

        if len(quotes) < windowSize * 2 + 1:
            logger.info(f"数据不足 stock_code={stockCode} count={len(quotes)}")
            return None

        highPrices = [q.highPrice for q in quotes]
        tradeDates = [q.tradeDate for q in quotes]
        closePrices = [q.closePrice for q in quotes]

        # 从后往前扫描，找到第一个满足条件的局部极大值
        for i in range(len(highPrices) - windowSize - 1, windowSize - 1, -1):
            # 条件3：高点后面至少有 windowSize 天数据
            if i + windowSize >= len(highPrices):
                continue

            # 条件1：在窗口内是最大值
            windowSlice = highPrices[i - windowSize: i + windowSize + 1]
            if highPrices[i] != max(windowSlice):
                continue

            # 条件2：高点之后有明显回撤
            hp = highPrices[i]
            afterMin = min(closePrices[i + 1: min(i + windowSize + 1, len(closePrices))])
            dropPct = (hp - afterMin) / hp if hp > 0 else Decimal("0")

            if dropPct < minDropPct:
                continue

            # 找到了有效高点，判断是否为历史新高
            allTimeHigh = (
                db.query(func.max(DailyQuote.highPrice))
                .filter(DailyQuote.stockCode == stockCode)
                .scalar()
            )
            highType = "history_high" if hp >= allTimeHigh else "local_high"

            # 清除该股票旧的 active 前高，写入新的
            db.query(PreviousHigh).filter(
                PreviousHigh.stockCode == stockCode,
                PreviousHigh.status == "active",
            ).delete()

            ph = PreviousHigh(
                stockCode=stockCode,
                highPrice=hp,
                highDate=tradeDates[i],
                lookbackDays=lookbackDays,
                highType=highType,
                status="active",
            )
            db.add(ph)
            db.commit()

            logger.info(f"前高识别完成 stock_code={stockCode} high={hp} date={tradeDates[i]}")
            return ph

        # 没有找到有效高点
        logger.info(f"未找到有效前高 stock_code={stockCode}")
        return None

    except Exception as e:
        db.rollback()
        logger.error(f"前高识别失败 stock_code={stockCode} 错误={e}", exc_info=True)
        raise


def analyzeHistoricalBreakouts(
    db: Session,
    stockCode: str,
    params: dict | None = None,
) -> BreakoutAnalysis | None:
    """
    遍历全部历史日线，滚动追踪局部高点，
    每次价格接近高点时记录事件，统计突破成功率。
    """
    if params is None:
        params = DEFAULT_PARAMS

    windowSize = params.get("windowSize", 5)
    minDropPct = Decimal(str(params.get("minDropPct", 0.05)))
    approachPct = Decimal(str(params.get("approachPct", 0.95)))
    observeDays = params.get("observeDays", 20)

    try:
        # 获取当前有效前高
        currentHigh = (
            db.query(PreviousHigh)
            .filter(
                PreviousHigh.stockCode == stockCode,
                PreviousHigh.status == "active",
            )
            .first()
        )
        if not currentHigh:
            return None

        # 获取全部历史日线（升序）
        allQuotes = (
            db.query(DailyQuote)
            .filter(DailyQuote.stockCode == stockCode)
            .order_by(DailyQuote.tradeDate.asc())
            .all()
        )

        if len(allQuotes) < windowSize * 2 + 1:
            return None

        highPrices = [q.highPrice for q in allQuotes]
        closePrices = [q.closePrice for q in allQuotes]
        tradeDates = [q.tradeDate for q in allQuotes]

        events = []
        totalApproach = 0
        successCount = 0
        failCount = 0

        # 滚动追踪局部高点
        trackedHigh = None
        trackedHighIdx = None
        approachIdx = None  # 记录接近事件的起始索引

        for i in range(windowSize, len(highPrices)):
            # 尝试识别新的局部高点
            if i + windowSize < len(highPrices):
                windowSlice = highPrices[i - windowSize: i + windowSize + 1]
                if highPrices[i] == max(windowSlice):
                    # 检查回撤
                    afterEnd = min(i + windowSize + 1, len(closePrices))
                    if afterEnd > i + 1:
                        afterMin = min(closePrices[i + 1: afterEnd])
                        dropPct = (highPrices[i] - afterMin) / highPrices[i] if highPrices[i] > 0 else Decimal("0")
                        if dropPct >= minDropPct:
                            # 如果有正在追踪的事件，先结束它
                            if approachIdx is not None and trackedHigh is not None:
                                event = _resolveEvent(
                                    closePrices, tradeDates, highPrices,
                                    trackedHigh, trackedHighIdx, approachIdx, i, observeDays,
                                )
                                if event:
                                    events.append(event)
                                    totalApproach += 1
                                    if event["result"] == "success":
                                        successCount += 1
                                    else:
                                        failCount += 1
                                approachIdx = None

                            # 更新追踪的高点
                            trackedHigh = highPrices[i]
                            trackedHighIdx = i

            # 如果有追踪的高点，检查是否接近
            if trackedHigh is not None and approachIdx is None and i > trackedHighIdx:
                if closePrices[i] >= trackedHigh * approachPct:
                    approachIdx = i

        # 处理最后一个未完成的事件
        if approachIdx is not None and trackedHigh is not None:
            event = _resolveEvent(
                closePrices, tradeDates, highPrices,
                trackedHigh, trackedHighIdx, approachIdx, len(closePrices), observeDays,
            )
            if event:
                events.append(event)
                totalApproach += 1
                if event["result"] == "success":
                    successCount += 1
                else:
                    failCount += 1

        # 计算成功率
        rate = None
        if totalApproach > 0:
            rate = round(Decimal(successCount) / Decimal(totalApproach) * 100, 2)

        # 写入或更新 breakout_analysis
        analysis = (
            db.query(BreakoutAnalysis)
            .filter(BreakoutAnalysis.stockCode == stockCode)
            .first()
        )
        if not analysis:
            analysis = BreakoutAnalysis(stockCode=stockCode)
            db.add(analysis)

        analysis.previousHighId = currentHigh.id
        analysis.currentHighPrice = currentHigh.highPrice
        analysis.currentHighDate = currentHigh.highDate
        analysis.totalApproachCount = totalApproach
        analysis.breakoutSuccessCount = successCount
        analysis.breakoutFailCount = failCount
        analysis.successRate = rate
        analysis.historyEvents = json.dumps(
            _serializeEvents(events), ensure_ascii=False
        )
        analysis.analyzedAt = datetime.now()

        db.commit()
        logger.info(
            f"历史突破分析完成 stock_code={stockCode} "
            f"total={totalApproach} success={successCount} fail={failCount}"
        )
        return analysis

    except Exception as e:
        db.rollback()
        logger.error(f"历史突破分析失败 stock_code={stockCode} 错误={e}", exc_info=True)
        raise


def _resolveEvent(
    closePrices: list,
    tradeDates: list,
    highPrices: list,
    trackedHigh: Decimal,
    trackedHighIdx: int,
    approachIdx: int,
    endBound: int,
    observeDays: int,
) -> dict | None:
    """判断一次接近事件的结果"""
    observeEnd = min(approachIdx + observeDays, endBound)
    if observeEnd <= approachIdx:
        return None

    approachPrice = closePrices[approachIdx]
    eventDate = tradeDates[approachIdx]

    # 在观察期内是否有收盘价站上前高
    success = False
    maxGainPct = Decimal("0")
    maxDropPct = Decimal("0")
    daysToResult = 0

    for j in range(approachIdx, observeEnd):
        pctFromHigh = (closePrices[j] - trackedHigh) / trackedHigh * 100 if trackedHigh > 0 else Decimal("0")
        if pctFromHigh > maxGainPct:
            maxGainPct = pctFromHigh
        pctDrop = (closePrices[j] - approachPrice) / approachPrice * 100 if approachPrice > 0 else Decimal("0")
        if pctDrop < maxDropPct:
            maxDropPct = pctDrop

        if not success and closePrices[j] >= trackedHigh:
            success = True
            daysToResult = j - approachIdx

    if not success:
        # 找最大跌幅对应的天数
        for j in range(approachIdx, observeEnd):
            pctDrop = (closePrices[j] - approachPrice) / approachPrice * 100 if approachPrice > 0 else Decimal("0")
            if pctDrop == maxDropPct:
                daysToResult = j - approachIdx
                break

    return {
        "eventDate": eventDate,
        "highPrice": trackedHigh,
        "approachPrice": approachPrice,
        "result": "success" if success else "failed",
        "maxGainPct": float(round(maxGainPct, 2)),
        "maxDropPct": float(round(maxDropPct, 2)),
        "daysToResult": daysToResult,
    }


def _serializeEvents(events: list[dict]) -> list[dict]:
    """序列化事件列表，处理 Decimal 和 date 类型"""
    result = []
    for e in events:
        item = {}
        for k, v in e.items():
            if isinstance(v, Decimal):
                item[k] = float(v)
            elif isinstance(v, date):
                item[k] = v.isoformat()
            else:
                item[k] = v
        result.append(item)
    return result


def checkBreakoutSignals(
    db: Session,
    stockCode: str,
    params: dict | None = None,
) -> list[Signal]:
    """
    检查某只股票的突破信号（简化为3种）：
    - approaching: 收盘价 >= 高点 × approachPct 且 < 高点
    - breakout: 收盘价 >= 高点
    - failed: 已有approaching信号但回落到 approachPct 以下
    """
    if params is None:
        params = DEFAULT_PARAMS

    approachPct = Decimal(str(params.get("approachPct", 0.95)))

    try:
        stock = db.query(Stock).filter(Stock.stockCode == stockCode).first()
        if not stock:
            return []

        # 获取当前有效前高
        activeHigh = (
            db.query(PreviousHigh)
            .filter(
                PreviousHigh.stockCode == stockCode,
                PreviousHigh.status == "active",
            )
            .first()
        )
        if not activeHigh:
            return []

        # 获取最新行情
        latestQuote = (
            db.query(DailyQuote)
            .filter(DailyQuote.stockCode == stockCode)
            .order_by(DailyQuote.tradeDate.desc())
            .first()
        )
        if not latestQuote:
            return []

        currentClose = latestQuote.closePrice
        currentDate = latestQuote.tradeDate
        highPrice = activeHigh.highPrice

        # 获取历史分析的成功率
        analysis = (
            db.query(BreakoutAnalysis)
            .filter(BreakoutAnalysis.stockCode == stockCode)
            .first()
        )
        successRate = analysis.successRate if analysis else None

        # 去重检查
        def signalExists(signalType: str) -> bool:
            return (
                db.query(Signal)
                .filter(
                    Signal.stockCode == stockCode,
                    Signal.previousHighId == activeHigh.id,
                    Signal.signalType == signalType,
                    Signal.signalDate == currentDate,
                )
                .first()
                is not None
            )

        newSignals = []
        approachThreshold = highPrice * approachPct

        # approaching: 接近前高
        if currentClose >= approachThreshold and currentClose < highPrice:
            if not signalExists("approaching"):
                rateStr = f"，历史成功率{successRate}%" if successRate is not None else ""
                signal = Signal(
                    stockCode=stockCode,
                    stockName=stock.stockName,
                    signalType="approaching",
                    signalDate=currentDate,
                    previousHighId=activeHigh.id,
                    previousHighPrice=highPrice,
                    triggerPrice=currentClose,
                    closePrice=currentClose,
                    successRate=successRate,
                    description=f"{stock.stockName}接近前高{highPrice}，收盘{currentClose}{rateStr}",
                )
                db.add(signal)
                newSignals.append(signal)

        # breakout: 突破前高
        elif currentClose >= highPrice:
            if not signalExists("breakout"):
                # 检查是否已有历史 breakout
                existingBreakout = (
                    db.query(Signal)
                    .filter(
                        Signal.stockCode == stockCode,
                        Signal.previousHighId == activeHigh.id,
                        Signal.signalType == "breakout",
                    )
                    .first()
                )
                if not existingBreakout:
                    rateStr = f"，历史成功率{successRate}%" if successRate is not None else ""
                    signal = Signal(
                        stockCode=stockCode,
                        stockName=stock.stockName,
                        signalType="breakout",
                        signalDate=currentDate,
                        previousHighId=activeHigh.id,
                        previousHighPrice=highPrice,
                        triggerPrice=currentClose,
                        closePrice=currentClose,
                        successRate=successRate,
                        description=f"{stock.stockName}突破前高{highPrice}，收盘{currentClose}{rateStr}",
                    )
                    db.add(signal)
                    newSignals.append(signal)

        # failed: 曾接近但回落
        elif currentClose < approachThreshold:
            # 检查是否有该前高的 approaching 信号
            hasApproaching = (
                db.query(Signal)
                .filter(
                    Signal.stockCode == stockCode,
                    Signal.previousHighId == activeHigh.id,
                    Signal.signalType == "approaching",
                )
                .first()
            )
            if hasApproaching:
                existingFailed = (
                    db.query(Signal)
                    .filter(
                        Signal.stockCode == stockCode,
                        Signal.previousHighId == activeHigh.id,
                        Signal.signalType == "failed",
                    )
                    .first()
                )
                if not existingFailed and not signalExists("failed"):
                    signal = Signal(
                        stockCode=stockCode,
                        stockName=stock.stockName,
                        signalType="failed",
                        signalDate=currentDate,
                        previousHighId=activeHigh.id,
                        previousHighPrice=highPrice,
                        triggerPrice=currentClose,
                        closePrice=currentClose,
                        successRate=successRate,
                        description=f"{stock.stockName}突破失败，前高{highPrice}，收盘{currentClose}",
                    )
                    db.add(signal)
                    newSignals.append(signal)

        db.commit()
        logger.info(f"突破检测完成 stock_code={stockCode} 新信号={len(newSignals)}")
        return newSignals

    except Exception as e:
        db.rollback()
        logger.error(f"突破检测失败 stock_code={stockCode} 错误={e}", exc_info=True)
        raise


def getBreakoutAnalysis(db: Session, stockCode: str) -> dict | None:
    """获取某只股票的突破分析数据，供API调用"""
    stock = db.query(Stock).filter(Stock.stockCode == stockCode).first()
    if not stock:
        return None

    activeHigh = (
        db.query(PreviousHigh)
        .filter(
            PreviousHigh.stockCode == stockCode,
            PreviousHigh.status == "active",
        )
        .first()
    )

    analysis = (
        db.query(BreakoutAnalysis)
        .filter(BreakoutAnalysis.stockCode == stockCode)
        .first()
    )

    latestQuote = (
        db.query(DailyQuote)
        .filter(DailyQuote.stockCode == stockCode)
        .order_by(DailyQuote.tradeDate.desc())
        .first()
    )

    # 判断当前状态
    currentStatus = "none"
    latestClose = None
    if latestQuote and activeHigh:
        latestClose = latestQuote.closePrice
        approachPct = Decimal(str(DEFAULT_PARAMS.get("approachPct", 0.95)))
        if latestClose >= activeHigh.highPrice:
            currentStatus = "breakout"
        elif latestClose >= activeHigh.highPrice * approachPct:
            currentStatus = "approaching"
        else:
            currentStatus = "below"

    historyEvents = []
    if analysis and analysis.historyEvents:
        try:
            historyEvents = json.loads(analysis.historyEvents)
        except json.JSONDecodeError:
            pass

    return {
        "stockCode": stockCode,
        "stockName": stock.stockName,
        "currentHigh": {
            "highPrice": float(activeHigh.highPrice) if activeHigh else None,
            "highDate": activeHigh.highDate.isoformat() if activeHigh else None,
            "status": activeHigh.status if activeHigh else None,
        } if activeHigh else None,
        "analysis": {
            "totalApproachCount": analysis.totalApproachCount if analysis else 0,
            "breakoutSuccessCount": analysis.breakoutSuccessCount if analysis else 0,
            "breakoutFailCount": analysis.breakoutFailCount if analysis else 0,
            "successRate": float(analysis.successRate) if analysis and analysis.successRate else 0,
        },
        "historyEvents": historyEvents,
        "currentStatus": currentStatus,
        "latestClose": float(latestClose) if latestClose else None,
    }


def runFullDetection(db: Session, watchList: list[str], params: dict | None = None) -> dict:
    """对关注列表中所有股票执行完整检测"""
    result = {"detected": 0, "signals": 0, "errors": []}

    for stockCode in watchList:
        try:
            findLatestPreviousHigh(db, stockCode, params)
            analyzeHistoricalBreakouts(db, stockCode, params)
            signals = checkBreakoutSignals(db, stockCode, params)
            result["detected"] += 1
            result["signals"] += len(signals)
        except Exception as e:
            result["errors"].append({"stockCode": stockCode, "error": str(e)})
            logger.error(f"检测失败 stock_code={stockCode} 错误={e}", exc_info=True)

    logger.info(
        f"全量检测完成 检测={result['detected']} 信号={result['signals']} 错误={len(result['errors'])}"
    )
    return result
