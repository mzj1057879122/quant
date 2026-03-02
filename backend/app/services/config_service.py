import json

from sqlalchemy.orm import Session

from app.models.user_config import UserConfig
from app.utils.logger import setupLogger

logger = setupLogger("config_service")

# 默认配置
DEFAULT_CONFIGS = {
    "watch_list": {
        "value": "[]",
        "description": "关注的股票代码列表",
    },
    "notify_enabled": {
        "value": "true",
        "description": "是否开启微信推送",
    },
    "server_chan_key": {
        "value": '""',
        "description": "Server酱SendKey",
    },
    "detection_params": {
        "value": json.dumps({
            "lookbackDays": 250,
            "windowSize": 5,
            "minDropPct": 0.05,
            "approachPct": 0.95,
            "observeDays": 20,
        }),
        "description": "检测算法参数",
    },
    "notify_types": {
        "value": json.dumps(["approaching", "breakout", "failed"]),
        "description": "需要推送的信号类型",
    },
}


def initDefaultConfigs(db: Session) -> None:
    """初始化默认配置（如果不存在则创建）"""
    for key, conf in DEFAULT_CONFIGS.items():
        existing = db.query(UserConfig).filter(UserConfig.configKey == key).first()
        if not existing:
            config = UserConfig(
                configKey=key,
                configValue=conf["value"],
                description=conf["description"],
            )
            db.add(config)
    db.commit()
    logger.info("默认配置初始化完成")


def getConfig(db: Session, key: str) -> str | None:
    """获取配置值"""
    config = db.query(UserConfig).filter(UserConfig.configKey == key).first()
    return config.configValue if config else None


def getConfigParsed(db: Session, key: str):
    """获取配置值并解析JSON"""
    value = getConfig(db, key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def setConfig(db: Session, key: str, value: str) -> UserConfig:
    """设置配置值"""
    config = db.query(UserConfig).filter(UserConfig.configKey == key).first()
    if config:
        config.configValue = value
    else:
        config = UserConfig(configKey=key, configValue=value)
        db.add(config)
    db.commit()
    return config


def getAllConfigs(db: Session) -> list[UserConfig]:
    """获取所有配置"""
    return db.query(UserConfig).all()


def getWatchList(db: Session) -> list[str]:
    """获取关注股票列表"""
    value = getConfigParsed(db, "watch_list")
    return value if isinstance(value, list) else []


def setWatchList(db: Session, stockCodes: list[str]) -> None:
    """设置关注股票列表"""
    setConfig(db, "watch_list", json.dumps(stockCodes))


def getDetectionParams(db: Session) -> dict:
    """获取检测算法参数"""
    value = getConfigParsed(db, "detection_params")
    if isinstance(value, dict):
        return value
    from app.services.detection_service import DEFAULT_PARAMS
    return DEFAULT_PARAMS
