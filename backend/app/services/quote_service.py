import random
import time
from datetime import date, timedelta
from decimal import Decimal

import akshare as ak
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.daily_quote import DailyQuote
from app.services.stock_service import getStockByCode
from app.utils.logger import setupLogger

logger = setupLogger("quote_service")

# 数据源配置：腾讯优先，腾讯TX备用，东方财富兜底
_SOURCE_ORDER = ["tencent", "tencent_tx", "eastmoney"]


def _getMarketPrefix(stockCode: str) -> str:
    """根据股票代码判断市场前缀（腾讯数据源需要）"""
    if stockCode.startswith("6"):
        return "sh"
    return "sz"


def _fetchFromTencent(stockCode: str, startDate: str) -> pd.DataFrame:
    """腾讯数据源：stock_zh_a_daily"""
    symbol = _getMarketPrefix(stockCode) + stockCode
    df = ak.stock_zh_a_daily(symbol=symbol, adjust="qfq")
    if df.empty:
        return df
    # 按日期过滤增量
    df["date"] = pd.to_datetime(df["date"]).dt.date
    cutoff = date(int(startDate[:4]), int(startDate[4:6]), int(startDate[6:]))
    df = df[df["date"] >= cutoff]
    # 统一列名
    df = df.rename(columns={
        "date": "tradeDate",
        "open": "openPrice",
        "close": "closePrice",
        "high": "highPrice",
        "low": "lowPrice",
        "volume": "volume",
        "amount": "turnover",
    })
    return df


def _fetchFromTencentTx(stockCode: str, startDate: str, endDate: str) -> pd.DataFrame:
    """腾讯TX数据源：stock_zh_a_hist_tx（不同接口，独立限流）"""
    symbol = _getMarketPrefix(stockCode) + stockCode
    df = ak.stock_zh_a_hist_tx(symbol=symbol, adjust="qfq")
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.date
    cutoff = date(int(startDate[:4]), int(startDate[4:6]), int(startDate[6:]))
    endD = date(int(endDate[:4]), int(endDate[4:6]), int(endDate[6:]))
    df = df[(df["date"] >= cutoff) & (df["date"] <= endD)]
    df = df.rename(columns={
        "date": "tradeDate",
        "open": "openPrice",
        "close": "closePrice",
        "high": "highPrice",
        "low": "lowPrice",
        "volume": "volume",
        "amount": "turnover",
    })
    return df


def _fetchFromEastmoney(stockCode: str, startDate: str, endDate: str) -> pd.DataFrame:
    """东方财富数据源：stock_zh_a_hist"""
    df = ak.stock_zh_a_hist(
        symbol=stockCode,
        period="daily",
        start_date=startDate,
        end_date=endDate,
        adjust="qfq",
    )
    if df.empty:
        return df
    # 统一列名
    tradeDate = df["日期"]
    if tradeDate.dtype == object:
        tradeDate = pd.to_datetime(tradeDate).dt.date
    df = df.rename(columns={
        "日期": "tradeDate",
        "开盘": "openPrice",
        "收盘": "closePrice",
        "最高": "highPrice",
        "最低": "lowPrice",
        "成交量": "volume",
        "成交额": "turnover",
        "涨跌幅": "changePct",
    })
    df["tradeDate"] = tradeDate
    return df


def _fetchWithFallback(stockCode: str, startDate: str, endDate: str) -> pd.DataFrame:
    """
    双数据源自动切换：优先腾讯，失败则尝试东方财富。
    每次请求失败后记录日志，不硬冲。
    """
    for source in _SOURCE_ORDER:
        try:
            if source == "tencent":
                df = _fetchFromTencent(stockCode, startDate)
            elif source == "tencent_tx":
                df = _fetchFromTencentTx(stockCode, startDate, endDate)
            else:
                df = _fetchFromEastmoney(stockCode, startDate, endDate)
            if not df.empty:
                logger.info(f"数据源={source} stock_code={stockCode} rows={len(df)}")
                return df
        except Exception as e:
            logger.error(f"数据源={source}失败 stock_code={stockCode} 错误={e}")
            # 切换数据源前等一下
            time.sleep(random.uniform(1, 2))

    # 全部失败返回空
    return pd.DataFrame()


def fetchDailyQuotes(
    db: Session,
    stockCode: str,
    startDate: str | None = None,
    endDate: str | None = None,
) -> int:
    """
    拉取某只股票的日线数据并存储。
    增量拉取：查询库中最新日期，只拉取之后的数据。
    双数据源：腾讯优先，东方财富备用。
    """
    try:
        if not startDate:
            latestDate = (
                db.query(func.max(DailyQuote.tradeDate))
                .filter(DailyQuote.stockCode == stockCode)
                .scalar()
            )
            if latestDate:
                startDate = (latestDate + timedelta(days=1)).strftime("%Y%m%d")
            else:
                startDate = "20240101"

        if not endDate:
            endDate = date.today().strftime("%Y%m%d")

        df = _fetchWithFallback(stockCode, startDate, endDate)

        if df.empty:
            logger.info(f"无新数据 stock_code={stockCode}")
            return 0

        # 如果没有 changePct 列，从收盘价计算
        if "changePct" not in df.columns:
            df = df.sort_values("tradeDate").reset_index(drop=True)
            df["changePct"] = df["closePrice"].pct_change() * 100
            # 第一条用DB中前一天收盘价补算
            if pd.isna(df.iloc[0]["changePct"]):
                prevClose = (
                    db.query(DailyQuote.closePrice)
                    .filter(DailyQuote.stockCode == stockCode)
                    .order_by(DailyQuote.tradeDate.desc())
                    .first()
                )
                if prevClose and prevClose[0]:
                    df.at[0, "changePct"] = (float(df.iloc[0]["closePrice"]) / float(prevClose[0]) - 1) * 100

        newCount = 0
        for _, row in df.iterrows():
            tradeDate = row["tradeDate"]
            if isinstance(tradeDate, str):
                tradeDate = date.fromisoformat(tradeDate)

            existing = (
                db.query(DailyQuote)
                .filter(
                    DailyQuote.stockCode == stockCode,
                    DailyQuote.tradeDate == tradeDate,
                )
                .first()
            )
            if existing:
                continue

            def safeDecimal(val):
                if val is None or str(val).strip() == "":
                    return Decimal("0")
                try:
                    fval = float(val)
                except (ValueError, TypeError):
                    return Decimal("0")
                if pd.isna(fval):
                    return Decimal("0")
                return Decimal(str(fval))

            quote = DailyQuote(
                stockCode=stockCode,
                tradeDate=tradeDate,
                openPrice=safeDecimal(row["openPrice"]),
                closePrice=safeDecimal(row["closePrice"]),
                highPrice=safeDecimal(row["highPrice"]),
                lowPrice=safeDecimal(row["lowPrice"]),
                volume=int(row["volume"]) if pd.notna(row["volume"]) else 0,
                turnover=safeDecimal(row["turnover"]),
                changePct=Decimal(str(row["changePct"])) if "changePct" in row and pd.notna(row.get("changePct")) else None,
            )
            db.add(quote)
            newCount += 1

        db.commit()
        logger.info(f"行情拉取完成 stock_code={stockCode} count={newCount}")
        return newCount

    except Exception as e:
        db.rollback()
        logger.error(
            f"行情拉取失败 stock_code={stockCode} start_date={startDate} end_date={endDate} 错误={e}",
            exc_info=True,
        )
        raise


def fetchAllWatchListQuotes(db: Session, watchList: list[str]) -> dict:
    """批量拉取关注列表中所有股票的行情数据"""
    result = {"success": 0, "failed": 0, "details": []}

    for stockCode in watchList:
        try:
            count = fetchDailyQuotes(db, stockCode)
            result["success"] += 1
            result["details"].append({"stockCode": stockCode, "count": count, "status": "ok"})
        except Exception as e:
            result["failed"] += 1
            result["details"].append({"stockCode": stockCode, "error": str(e), "status": "fail"})
            logger.error(f"批量拉取失败 stock_code={stockCode} 错误={e}", exc_info=True)

        # 随机间隔2-10秒，模拟人工操作节奏
        time.sleep(random.uniform(5, 10))

    logger.info(f"批量拉取完成 成功={result['success']} 失败={result['failed']}")
    return result


def getQuotesByStockCode(
    db: Session,
    stockCode: str,
    startDate: date | None = None,
    endDate: date | None = None,
    limit: int = 250,
) -> list[DailyQuote]:
    """获取某只股票的日线数据"""
    query = db.query(DailyQuote).filter(DailyQuote.stockCode == stockCode)

    if startDate:
        query = query.filter(DailyQuote.tradeDate >= startDate)
    if endDate:
        query = query.filter(DailyQuote.tradeDate <= endDate)

    return query.order_by(DailyQuote.tradeDate.desc()).limit(limit).all()


def calcExpmaForStock(db: Session, stockCode: str) -> int:
    """
    计算并更新某只股票所有历史记录的 EXPMA(5/13/34/89) 和 MACD(DIF/DEA/柱)。
    EMA 公式：EMA(t) = close(t) * k + EMA(t-1) * (1-k)，k = 2/(n+1)
    MACD：EMA12/EMA26 算 DIF，EMA9(DIF) 算 DEA，柱=(DIF-DEA)*2
    初始值：EMA取第一条收盘价，DEA取第一条DIF值。
    """
    rows = (
        db.query(DailyQuote)
        .filter(DailyQuote.stockCode == stockCode)
        .order_by(DailyQuote.tradeDate.asc())
        .all()
    )
    if not rows:
        return 0

    periods = [5, 13, 34, 89]
    k = {n: 2 / (n + 1) for n in periods}
    ema = {}

    # MACD 参数
    k12 = 2 / 13
    k26 = 2 / 27
    k9 = 2 / 10
    ema12 = ema26 = dea = 0.0

    for i, row in enumerate(rows):
        close = float(row.closePrice)
        if i == 0:
            for n in periods:
                ema[n] = close
            ema12 = close
            ema26 = close
            dif = 0.0
            dea = 0.0
        else:
            for n in periods:
                ema[n] = close * k[n] + ema[n] * (1 - k[n])
            ema12 = close * k12 + ema12 * (1 - k12)
            ema26 = close * k26 + ema26 * (1 - k26)
            dif = ema12 - ema26
            dea = dif * k9 + dea * (1 - k9)

        row.expma5 = round(ema[5], 3)
        row.expma13 = round(ema[13], 3)
        row.expma34 = round(ema[34], 3)
        row.expma89 = round(ema[89], 3)
        row.macdDiff = round(dif, 4)
        row.macdDea = round(dea, 4)
        row.macdBar = round((dif - dea) * 2, 4)

    db.commit()
    return len(rows)


def calcExpmaForAll(db: Session) -> dict:
    """遍历所有有数据的股票，批量计算 EXPMA"""
    from sqlalchemy import distinct
    stocks = [r[0] for r in db.query(distinct(DailyQuote.stockCode)).all()]
    success, failed = 0, 0
    for stockCode in stocks:
        try:
            calcExpmaForStock(db, stockCode)
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"EXPMA计算失败 stock_code={stockCode} 错误={e}", exc_info=True)
    logger.info(f"EXPMA批量计算完成 成功={success} 失败={failed}")
    return {"success": success, "failed": failed}


def getLatestQuote(db: Session, stockCode: str) -> DailyQuote | None:
    """获取最新一条行情"""
    return (
        db.query(DailyQuote)
        .filter(DailyQuote.stockCode == stockCode)
        .order_by(DailyQuote.tradeDate.desc())
        .first()
    )


def calcWeeklyStats(db: Session, stockCode: str) -> int:
    """
    计算某只股票的周线数据并存入 weekly_quote 表。
    按自然周（周一到周五）聚合：open=周一开盘，close=周五收盘，high=周内最高，low=周内最低，volume=周内累计。
    同时计算周线 EMA(5/13/34)，upsert（已存在则更新）。
    """
    from datetime import timedelta
    from decimal import Decimal
    from app.models.weekly_quote import WeeklyQuote

    rows = (
        db.query(DailyQuote)
        .filter(DailyQuote.stockCode == stockCode)
        .order_by(DailyQuote.tradeDate.asc())
        .all()
    )
    if not rows:
        return 0

    # 按自然周分组：以周一日期为 key
    weeks: dict = {}
    for row in rows:
        # weekday(): 周一=0, ..., 周日=6
        monday = row.tradeDate - timedelta(days=row.tradeDate.weekday())
        if monday not in weeks:
            weeks[monday] = []
        weeks[monday].append(row)

    # 按周一日期排序，聚合各周
    periods = [5, 13, 34]
    k = {n: 2 / (n + 1) for n in periods}
    ema: dict = {}
    initialized = False

    upsertCount = 0
    for monday in sorted(weeks.keys()):
        dayRows = sorted(weeks[monday], key=lambda r: r.tradeDate)
        openPrice = float(dayRows[0].openPrice)
        closePrice = float(dayRows[-1].closePrice)
        highPrice = max(float(r.highPrice) for r in dayRows)
        lowPrice = min(float(r.lowPrice) for r in dayRows)
        volume = sum(r.volume for r in dayRows)

        # EMA 迭代
        if not initialized:
            for n in periods:
                ema[n] = closePrice
            initialized = True
        else:
            for n in periods:
                ema[n] = closePrice * k[n] + ema[n] * (1 - k[n])

        existing = (
            db.query(WeeklyQuote)
            .filter(WeeklyQuote.stockCode == stockCode, WeeklyQuote.weekStart == monday)
            .first()
        )
        if existing:
            existing.openPrice = Decimal(str(round(openPrice, 3)))
            existing.closePrice = Decimal(str(round(closePrice, 3)))
            existing.highPrice = Decimal(str(round(highPrice, 3)))
            existing.lowPrice = Decimal(str(round(lowPrice, 3)))
            existing.volume = volume
            existing.expma5 = Decimal(str(round(ema[5], 3)))
            existing.expma13 = Decimal(str(round(ema[13], 3)))
            existing.expma34 = Decimal(str(round(ema[34], 3)))
        else:
            wq = WeeklyQuote(
                stockCode=stockCode,
                weekStart=monday,
                openPrice=Decimal(str(round(openPrice, 3))),
                closePrice=Decimal(str(round(closePrice, 3))),
                highPrice=Decimal(str(round(highPrice, 3))),
                lowPrice=Decimal(str(round(lowPrice, 3))),
                volume=volume,
                expma5=Decimal(str(round(ema[5], 3))),
                expma13=Decimal(str(round(ema[13], 3))),
                expma34=Decimal(str(round(ema[34], 3))),
            )
            db.add(wq)
        upsertCount += 1

    db.commit()
    logger.info(f"周线计算完成 stock_code={stockCode} weeks={upsertCount}")
    return upsertCount


def calcWeeklyForAll(db: Session) -> dict:
    """遍历所有有数据的股票，批量计算周线数据"""
    from sqlalchemy import distinct
    stocks = [r[0] for r in db.query(distinct(DailyQuote.stockCode)).all()]
    success, failed = 0, 0
    for stockCode in stocks:
        try:
            calcWeeklyStats(db, stockCode)
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"周线计算失败 stock_code={stockCode} 错误={e}", exc_info=True)
    logger.info(f"周线批量计算完成 成功={success} 失败={failed}")
    return {"success": success, "failed": failed}


def getWeeklyQuotes(db: Session, stockCode: str, limit: int = 52):
    """获取某只股票最近N周的周线数据"""
    from app.models.weekly_quote import WeeklyQuote
    return (
        db.query(WeeklyQuote)
        .filter(WeeklyQuote.stockCode == stockCode)
        .order_by(WeeklyQuote.weekStart.desc())
        .limit(limit)
        .all()
    )
