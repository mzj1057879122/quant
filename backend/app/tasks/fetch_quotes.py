from app.database import SessionLocal
from app.services.config_service import getWatchList
from app.services.quote_service import fetchAllWatchListQuotes
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger
from datetime import date

logger = setupLogger("task_fetch_quotes")


def runFetchQuotes() -> None:
    """定时任务：拉取关注股票的行情数据"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        watchList = getWatchList(db)
        if not watchList:
            logger.info("关注列表为空，跳过拉取")
            return

        result = fetchAllWatchListQuotes(db, watchList)
        logger.info(f"定时拉取完成 成功={result['success']} 失败={result['failed']}")
    except Exception as e:
        logger.error(f"定时拉取任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
