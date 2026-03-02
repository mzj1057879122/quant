import asyncio
from datetime import date

from app.database import SessionLocal
from app.services.config_service import getWatchList, getDetectionParams, getConfigParsed
from app.services.detection_service import runFullDetection
from app.services.notify_service import sendDailyNotification
from app.services.signal_service import getUnnotifiedSignals, markAsNotified
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_detect_signals")


def runDetectSignals() -> None:
    """定时任务：对关注股票执行前高检测"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        watchList = getWatchList(db)
        if not watchList:
            logger.info("关注列表为空，跳过检测")
            return

        params = getDetectionParams(db)
        result = runFullDetection(db, watchList, params)
        logger.info(f"定时检测完成 信号={result['signals']} 错误={len(result['errors'])}")
    except Exception as e:
        logger.error(f"定时检测任务异常 错误={e}", exc_info=True)
    finally:
        db.close()


def runSendNotifications() -> None:
    """定时任务：推送未通知的信号"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        notifyEnabled = getConfigParsed(db, "notify_enabled")
        if not notifyEnabled:
            logger.info("推送未开启，跳过")
            return

        signals = getUnnotifiedSignals(db)
        if not signals:
            logger.info("无待推送信号")
            return

        # 运行异步推送
        success = asyncio.run(sendDailyNotification(signals))
        if success:
            signalIds = [s.id for s in signals]
            markAsNotified(db, signalIds)
            logger.info(f"推送完成 count={len(signalIds)}")
        else:
            logger.error("推送失败", exc_info=False)
    except Exception as e:
        logger.error(f"推送任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
