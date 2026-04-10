import time

import akshare as ak

from app.utils.logger import setupLogger

logger = setupLogger("strong_service")

# 内存缓存：避免频繁打 THS 被封
_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 1800  # 30分钟


def getStrongStocks(
    maxDays: int = 5,
    minGainPct: float = 15.0,
    maxGainPct: float = 100.0,
    forceRefresh: bool = False,
) -> tuple[list[dict], bool]:
    """
    获取强势股（连续上涨筛选，仅主板：沪市60xxxx / 深市00xxxx）
    返回 (结果列表, 是否来自缓存)
    """
    now = time.time()
    fromCache = False

    if not forceRefresh and _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        df_raw = _cache["data"]
        fromCache = True
        logger.info(f"强势股使用缓存 age={int(now - _cache['ts'])}s")
    else:
        try:
            df_raw = ak.stock_rank_lxsz_ths()
        except Exception as e:
            logger.error(f"拉取同花顺连续上涨数据失败 错误={e}", exc_info=True)
            # 拉取失败时降级返回旧缓存
            if _cache["data"] is not None:
                logger.info("THS 拉取失败，降级使用旧缓存")
                df_raw = _cache["data"]
                fromCache = True
            else:
                raise Exception(f"获取强势股数据失败: {e}")

        if df_raw is None or len(df_raw) == 0:
            if _cache["data"] is not None:
                logger.info("THS 数据为空，降级使用旧缓存")
                df_raw = _cache["data"]
                fromCache = True
            else:
                logger.error("同花顺连续上涨数据为空")
                raise Exception("获取强势股数据为空")

        if not fromCache:
            _cache["data"] = df_raw
            _cache["ts"] = now

    # 筛选条件
    try:
        df = df_raw.copy()
        # 主板过滤：沪市 60xxxx，深市 00xxxx
        df = df[df["股票代码"].astype(str).str.match(r"^(60|00)\d{4}$")]
        df = df[df["连涨天数"] <= maxDays]
        df = df[df["连续涨跌幅"] >= minGainPct]
        df = df[df["连续涨跌幅"] <= maxGainPct]
        df = df.sort_values("连续涨跌幅", ascending=False)
    except Exception as e:
        logger.error(f"筛选强势股数据失败 错误={e}", exc_info=True)
        raise Exception(f"筛选强势股数据失败: {e}")

    result = []
    for row in df.itertuples():
        result.append({
            "stockCode": str(getattr(row, "股票代码", "")),
            "stockName": str(getattr(row, "股票简称", "")),
            "closePrice": float(getattr(row, "收盘价", 0) or 0),
            "daysUp": int(getattr(row, "连涨天数", 0) or 0),
            "gainPct": float(getattr(row, "连续涨跌幅", 0) or 0),
            "turnoverPct": float(getattr(row, "累计换手率", 0) or 0),
            "industry": str(getattr(row, "所属行业", "")),
        })

    cacheAge = int(now - _cache["ts"]) if fromCache else 0
    logger.info(f"强势股筛选完成 fromCache={fromCache} cacheAge={cacheAge}s maxDays={maxDays} minGainPct={minGainPct} maxGainPct={maxGainPct} count={len(result)}")
    return result, fromCache
