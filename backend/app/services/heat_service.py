import time
from datetime import date

import akshare as ak
from sqlalchemy.orm import Session

from app.models.stock_heat import StockHeat
from app.utils.logger import setupLogger

logger = setupLogger("heat_service")


def fetchXueqiuHeat() -> dict[str, dict]:
    """拉取雪球关注+讨论排行，返回 {stockCode: {followCount, followRank, tweetCount, tweetRank}}"""
    result = {}

    # 关注排行
    try:
        dfFollow = ak.stock_hot_follow_xq()
        if dfFollow is not None and len(dfFollow) > 0:
            for rank, row in enumerate(dfFollow.itertuples(), 1):
                code = str(getattr(row, "股票代码", ""))
                if not code:
                    continue
                raw = getattr(row, "关注", 0); count = int(raw) if raw == raw and raw is not None else 0
                result[code] = {"followCount": count, "followRank": rank, "tweetCount": 0, "tweetRank": 0}
            logger.info(f"雪球关注排行拉取完成 count={len(result)}")
    except Exception as e:
        logger.error(f"拉取雪球关注排行失败 错误={e}", exc_info=True)

    time.sleep(2)

    # 讨论排行
    try:
        dfTweet = ak.stock_hot_tweet_xq()
        if dfTweet is not None and len(dfTweet) > 0:
            for rank, row in enumerate(dfTweet.itertuples(), 1):
                code = str(getattr(row, "股票代码", ""))
                if not code:
                    continue
                raw = getattr(row, "关注", 0); count = int(raw) if raw == raw and raw is not None else 0
                if code in result:
                    result[code]["tweetCount"] = count
                    result[code]["tweetRank"] = rank
                else:
                    result[code] = {"followCount": 0, "followRank": 0, "tweetCount": count, "tweetRank": rank}
            logger.info(f"雪球讨论排行拉取完成")
    except Exception as e:
        logger.error(f"拉取雪球讨论排行失败 错误={e}", exc_info=True)

    return result


def fetchBaiduHotSearch() -> set[str]:
    """拉取百度热搜 TOP 股票代码集合"""
    result = set()
    try:
        df = ak.stock_hot_search_baidu(symbol="A股")
        if df is not None and len(df) > 0:
            for row in df.itertuples():
                code = str(getattr(row, "股票代码", ""))
                if code:
                    result.add(code)
            logger.info(f"百度热搜拉取完成 count={len(result)}")
    except Exception as e:
        logger.error(f"拉取百度热搜失败 错误={e}", exc_info=True)
    return result


def calcHeatScore(followRank: int, tweetRank: int, totalStocks: int, isBaiduHot: bool) -> int:
    """计算综合热度得分 0-100
    heatScore = 雪球关注排名分(40%) + 雪球讨论排名分(40%) + 百度热搜加分(20%)
    排名分：(totalStocks - rank) / totalStocks * 100，排名越靠前分越高
    """
    if totalStocks <= 0:
        totalStocks = 5000

    followScore = max(0, (totalStocks - followRank) / totalStocks * 100) if followRank > 0 else 0
    tweetScore = max(0, (totalStocks - tweetRank) / totalStocks * 100) if tweetRank > 0 else 0
    baiduScore = 100 if isBaiduHot else 0

    score = followScore * 0.4 + tweetScore * 0.4 + baiduScore * 0.2
    return max(0, min(100, round(score)))


def saveHeatData(db: Session, heatDate: date, xqData: dict[str, dict], baiduCodes: set[str]) -> int:
    """保存热度数据到 stock_heat 表，返回保存条数"""
    totalStocks = max(len(xqData), 5000)
    allCodes = set(xqData.keys()) | baiduCodes
    saved = 0

    for code in allCodes:
        xq = xqData.get(code, {})
        followCount = xq.get("followCount", 0)
        followRank = xq.get("followRank", 0)
        tweetCount = xq.get("tweetCount", 0)
        tweetRank = xq.get("tweetRank", 0)
        isBaiduHot = code in baiduCodes

        score = calcHeatScore(followRank, tweetRank, totalStocks, isBaiduHot)

        # 只保存有热度的（排名靠前或百度热搜）
        if score < 10 and not isBaiduHot:
            continue

        existing = db.query(StockHeat).filter(
            StockHeat.stockCode == code,
            StockHeat.heatDate == heatDate,
        ).first()

        if existing:
            existing.xqFollowCount = followCount
            existing.xqFollowRank = followRank
            existing.xqTweetCount = tweetCount
            existing.xqTweetRank = tweetRank
            existing.baiduHot = isBaiduHot
            existing.heatScore = score
        else:
            db.add(StockHeat(
                stockCode=code,
                heatDate=heatDate,
                xqFollowCount=followCount,
                xqFollowRank=followRank,
                xqTweetCount=tweetCount,
                xqTweetRank=tweetRank,
                baiduHot=isBaiduHot,
                heatScore=score,
            ))
        saved += 1

    db.commit()
    logger.info(f"热度数据保存完成 date={heatDate} saved={saved}")
    return saved


def getStockHeat(db: Session, stockCodes: list[str], heatDate: date | None = None) -> dict[str, dict]:
    """查询股票热度，返回 {stockCode: {heatScore, xqFollowRank, xqTweetRank, baiduHot}}"""
    if not stockCodes:
        return {}

    targetDate = heatDate or date.today()

    # 先查当天，没有则查最近一天
    rows = db.query(StockHeat).filter(
        StockHeat.stockCode.in_(stockCodes),
        StockHeat.heatDate == targetDate,
    ).all()

    if not rows:
        # 查最近有数据的日期
        latestRow = db.query(StockHeat).filter(
            StockHeat.heatDate <= targetDate,
        ).order_by(StockHeat.heatDate.desc()).first()
        if latestRow:
            rows = db.query(StockHeat).filter(
                StockHeat.stockCode.in_(stockCodes),
                StockHeat.heatDate == latestRow.heatDate,
            ).all()

    result = {}
    for r in rows:
        result[r.stockCode] = {
            "heatScore": r.heatScore,
            "xqFollowRank": r.xqFollowRank,
            "xqTweetRank": r.xqTweetRank,
            "baiduHot": r.baiduHot,
            "heatDate": r.heatDate.isoformat() if r.heatDate else None,
        }
    return result


def getHeatTop(db: Session, heatDate: date | None = None, limit: int = 50) -> list[dict]:
    """热度排行榜 TOP N"""
    targetDate = heatDate or date.today()

    # 先查当天
    rows = db.query(StockHeat).filter(
        StockHeat.heatDate == targetDate,
    ).order_by(StockHeat.heatScore.desc()).limit(limit).all()

    if not rows:
        latestRow = db.query(StockHeat).filter(
            StockHeat.heatDate <= targetDate,
        ).order_by(StockHeat.heatDate.desc()).first()
        if latestRow:
            rows = db.query(StockHeat).filter(
                StockHeat.heatDate == latestRow.heatDate,
            ).order_by(StockHeat.heatScore.desc()).limit(limit).all()

    return [
        {
            "stockCode": r.stockCode,
            "heatDate": r.heatDate.isoformat(),
            "heatScore": r.heatScore,
            "xqFollowCount": r.xqFollowCount,
            "xqFollowRank": r.xqFollowRank,
            "xqTweetCount": r.xqTweetCount,
            "xqTweetRank": r.xqTweetRank,
            "baiduHot": r.baiduHot,
        }
        for r in rows
    ]


def getStockHeatDetail(db: Session, stockCode: str, limit: int = 30) -> list[dict]:
    """单只股票热度历史"""
    rows = db.query(StockHeat).filter(
        StockHeat.stockCode == stockCode,
    ).order_by(StockHeat.heatDate.desc()).limit(limit).all()

    return [
        {
            "heatDate": r.heatDate.isoformat(),
            "heatScore": r.heatScore,
            "xqFollowCount": r.xqFollowCount,
            "xqFollowRank": r.xqFollowRank,
            "xqTweetCount": r.xqTweetCount,
            "xqTweetRank": r.xqTweetRank,
            "baiduHot": r.baiduHot,
        }
        for r in rows
    ]
