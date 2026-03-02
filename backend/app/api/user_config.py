import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import getDb
from app.schemas.user_config import UserConfigResponse, UserConfigUpdate, WatchListUpdate
from app.services import config_service

router = APIRouter(prefix="/config", tags=["用户配置"])


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


@router.put("/watch-list")
def updateWatchList(body: WatchListUpdate, db: Session = Depends(getDb)):
    """更新关注股票列表"""
    config_service.setWatchList(db, body.stockCodes)
    return {"message": "更新成功", "stockCodes": body.stockCodes}


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
