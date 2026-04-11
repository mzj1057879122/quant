from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.fetch_quotes import runFetchQuotes
from app.tasks.detect_signals import runDetectSignals, runSendNotifications
from app.tasks.fetch_heat import runFetchHeat
from app.tasks.fetch_morning_brief import runFetchMorningBrief
from app.tasks.daily_prediction import runDailyPrediction
from app.tasks.verify_predictions import runVerifyPredictions
from app.tasks.fetch_limit_up import runFetchLimitUp
from app.utils.logger import setupLogger

logger = setupLogger("scheduler")

scheduler = BackgroundScheduler()


def initScheduler() -> None:
    """初始化定时任务调度器"""

    # 每个交易日18:00拉取行情数据
    scheduler.add_job(
        runFetchQuotes,
        trigger=CronTrigger(hour=18, minute=0, day_of_week="mon-fri"),
        id="fetch_daily_quotes",
        name="拉取日线行情",
        replace_existing=True,
    )

    # 每个交易日18:30执行信号检测
    scheduler.add_job(
        runDetectSignals,
        trigger=CronTrigger(hour=18, minute=30, day_of_week="mon-fri"),
        id="detect_signals",
        name="检测突破信号",
        replace_existing=True,
    )

    # 每个交易日18:45推送通知
    scheduler.add_job(
        runSendNotifications,
        trigger=CronTrigger(hour=18, minute=45, day_of_week="mon-fri"),
        id="send_notifications",
        name="推送微信通知",
        replace_existing=True,
    )

    # 每个交易日15:30拉取股票热度数据
    scheduler.add_job(
        runFetchHeat,
        trigger=CronTrigger(hour=15, minute=30, day_of_week="mon-fri"),
        id="fetch_stock_heat",
        name="拉取股票热度",
        replace_existing=True,
    )

    # 每个交易日09:00（北京时间，UTC+8，即 UTC 01:00）采集盘前纪要
    scheduler.add_job(
        runFetchMorningBrief,
        trigger=CronTrigger(hour=1, minute=0, day_of_week="mon-fri"),
        id="fetch_morning_brief",
        name="采集盘前纪要",
        replace_existing=True,
    )

    # 每个交易日16:00（北京时间，UTC+8，即 UTC 08:00）验证昨日预测
    scheduler.add_job(
        runVerifyPredictions,
        trigger=CronTrigger(hour=8, minute=0, day_of_week="mon-fri"),
        id="verify_predictions",
        name="验证昨日预测",
        replace_existing=True,
    )

    # 每个交易日16:30（北京时间，UTC+8，即 UTC 08:30）执行每日预测打分
    scheduler.add_job(
        runDailyPrediction,
        trigger=CronTrigger(hour=8, minute=30, day_of_week="mon-fri"),
        id="daily_prediction",
        name="每日预测打分",
        replace_existing=True,
    )

    # 每个交易日16:00（北京时间，UTC+8，即 UTC 08:00）采集涨停板块数据
    scheduler.add_job(
        _runFetchLimitUp,
        trigger=CronTrigger(hour=8, minute=0, day_of_week="mon-fri"),
        id="fetch_limit_up",
        name="采集涨停板块",
        replace_existing=True,
    )

    # 每周六10:00同步股票列表
    scheduler.add_job(
        _runSyncStockList,
        trigger=CronTrigger(hour=10, minute=0, day_of_week="sat"),
        id="sync_stock_list",
        name="同步股票列表",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("定时任务调度器已启动")


def shutdownScheduler() -> None:
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已关闭")


def getSchedulerStatus() -> list[dict]:
    """获取所有任务状态"""
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "nextRunTime": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]


def _runSyncStockList() -> None:
    """同步股票列表（定时任务包装）"""
    from app.database import SessionLocal
    from app.services.stock_service import syncStockList

    db = SessionLocal()
    try:
        syncStockList(db)
    except Exception as e:
        logger.error(f"同步股票列表任务异常 错误={e}", exc_info=True)
    finally:
        db.close()


def _runFetchLimitUp() -> None:
    """采集涨停板块数据（定时任务包装）"""
    try:
        runFetchLimitUp()
    except Exception as e:
        logger.error(f"采集涨停板块任务异常 错误={e}", exc_info=True)
