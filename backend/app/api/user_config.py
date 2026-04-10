import json

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import getDb, SessionLocal
from app.schemas.user_config import UserConfigResponse, UserConfigUpdate, WatchListUpdate
from app.services import config_service
from app.services import quote_service
from app.utils.logger import setupLogger

router = APIRouter(prefix="/config", tags=["用户配置"])

logger = setupLogger("user_config")


@router.get("")
def getAllConfigs(db: Session = Depends(getDb)):
    """获取所有配置"""
    items = config_service.getAllConfigs(db)
    return {"items": items}


@router.get("/watch-list")
def getWatchList(db: Session = Depends(getDb)):
    """获取关注股票列表"""
    stockCodes = config_service.getWatchList(db)
    return {"stockCodes": stockCodes}


def _fetchQuotesInBackground(newStocks: list[str]):
    """后台任务：对每个新增股票拉取近2年日线数据"""
    db = SessionLocal()
    try:
        for code in newStocks:
            try:
                count = quote_service.fetchDailyQuotes(db, code, startDate="20240101")
                logger.info(f"后台拉取完成 stock_code={code} count={count}")
            except Exception as e:
                logger.error(f"后台拉取失败 stock_code={code} error={e}", exc_info=True)
    finally:
        db.close()


@router.put("/watch-list")
def updateWatchList(body: WatchListUpdate, background_tasks: BackgroundTasks, db: Session = Depends(getDb)):
    """更新关注股票列表，新增股票后台自动拉取近2年日线数据"""
    # 获取旧列表，找出新增股票
    oldStocks = config_service.getWatchList(db)
    oldSet = set(oldStocks)
    newStocks = [code for code in body.stockCodes if code not in oldSet]

    config_service.setWatchList(db, body.stockCodes)

    # 有新增股票时，后台异步拉取行情
    if newStocks:
        background_tasks.add_task(_fetchQuotesInBackground, newStocks)
        logger.info(f"新增股票，后台拉取日线数据 stocks={newStocks}")

    return {"message": "更新成功", "stockCodes": body.stockCodes, "newStocks": newStocks}


@router.get("/{key}", response_model=UserConfigResponse)
def getConfig(key: str, db: Session = Depends(getDb)):
    """获取某项配置"""
    from app.models.user_config import UserConfig
    config = db.query(UserConfig).filter(UserConfig.configKey == key).first()
    if not config:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.put("/{key}")
def updateConfig(key: str, body: UserConfigUpdate, db: Session = Depends(getDb)):
    """更新某项配置"""
    config = config_service.setConfig(db, key, body.configValue)
    return {"message": "更新成功", "configKey": key}
