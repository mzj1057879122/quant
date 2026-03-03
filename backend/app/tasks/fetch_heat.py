from datetime import date

from app.database import SessionLocal
from app.services.heat_service import fetchXueqiuHeat, fetchBaiduHotSearch, saveHeatData
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_fetch_heat")


def runFetchHeat() -> None:
    """定时任务：拉取股票热度数据（雪球+百度）"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        # 拉取雪球数据
        xqData = fetchXueqiuHeat()
        # 拉取百度热搜
        baiduCodes = fetchBaiduHotSearch()

        if not xqData and not baiduCodes:
            logger.error("雪球和百度数据均拉取失败")
            return

        # 保存到数据库
        saved = saveHeatData(db, today, xqData, baiduCodes)
        logger.info(f"热度数据拉取完成 date={today} saved={saved}")
    except Exception as e:
        logger.error(f"热度数据拉取任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
