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

# 数据源配置：优先腾讯，东方财富备用
_SOURCE_ORDER = ["tencent", "eastmoney"]


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


def getLatestQuote(db: Session, stockCode: str) -> DailyQuote | None:
    """获取最新一条行情"""
    return (
        db.query(DailyQuote)
        .filter(DailyQuote.stockCode == stockCode)
        .order_by(DailyQuote.tradeDate.desc())
        .first()
    )
