import time
from datetime import datetime, timezone

from fastapi import APIRouter, Query, HTTPException

from app.services import strong_service

router = APIRouter(prefix="/strong", tags=["强势股筛选"])


@router.get("/list")
def listStrongStocks(
    maxDays: int = Query(5, ge=1, le=20, description="最多连涨天数"),
    minGainPct: float = Query(15.0, ge=1.0, le=200.0, description="最低累计涨幅%"),
    maxGainPct: float = Query(100.0, ge=1.0, le=200.0, description="最高累计涨幅%"),
    forceRefresh: bool = Query(False, description="强制刷新缓存"),
):
    """获取强势股列表（30分钟缓存，仅主板）"""
    try:
        items, fromCache = strong_service.getStrongStocks(
            maxDays=maxDays,
            minGainPct=minGainPct,
            maxGainPct=maxGainPct,
            forceRefresh=forceRefresh,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cacheTs = strong_service._cache["ts"]
    dataUpdatedAt = datetime.fromtimestamp(cacheTs, tz=timezone.utc).isoformat() if cacheTs else None

    return {
        "items": items,
        "total": len(items),
        "fromCache": fromCache,
        "dataUpdatedAt": dataUpdatedAt,
        "respondedAt": datetime.now(timezone.utc).isoformat(),
    }
