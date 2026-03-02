from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.fetch_quotes import runFetchQuotes
from app.tasks.detect_signals import runDetectSignals, runSendNotifications
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
