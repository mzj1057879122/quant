import logging
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import getDb
from app.tasks.scheduler import getSchedulerStatus
from app.tasks.fetch_quotes import runFetchQuotes
from app.tasks.detect_signals import runDetectSignals, runSendNotifications

logger = logging.getLogger("system")

router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/health")
def healthCheck():
    """健康检查"""
    return {"status": "ok"}


@router.get("/task-status")
def taskStatus():
    """查看定时任务状态"""
    jobs = getSchedulerStatus()
    return {"jobs": jobs}


@router.post("/run-task/{taskName}")
def runTask(taskName: str, db: Session = Depends(getDb)):
    """手动触发指定任务"""
    taskMap = {
        "fetch_quotes": runFetchQuotes,
        "detect_signals": runDetectSignals,
        "send_notifications": runSendNotifications,
    }

    if taskName not in taskMap:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"未知任务: {taskName}，可选: {list(taskMap.keys())}",
        )

    taskMap[taskName]()
    return {"message": f"任务 {taskName} 执行完成"}


def _runBackfillLimitUp(startDate: str, endDate: str) -> None:
    """后台线程：执行涨停板块历史补采，进度写入日志文件"""
    import sys

    # 同时写到 /tmp/backfill-limit-up.log
    fileHandler = logging.FileHandler("/tmp/backfill-limit-up.log", mode="a", encoding="utf-8")
    fileHandler.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fileHandler.setFormatter(fmt)
    backfillLogger = logging.getLogger("fetch_limit_up")
    backfillLogger.addHandler(fileHandler)

    try:
        from app.tasks.fetch_limit_up import backfillLimitUpHistory
        summary = backfillLimitUpHistory(startDate, endDate)
        logger.info(f"补采完成 summary={summary}")
    except Exception as e:
        logger.error(f"补采任务异常 错误={e}", exc_info=True)
    finally:
        backfillLogger.removeHandler(fileHandler)
        fileHandler.close()


@router.post("/backfill-limit-up")
def backfillLimitUp(
    background_tasks: BackgroundTasks,
    startDate: str = "2025-01-01",
    endDate: str = "2025-12-31",
):
    """
    后台异步补采历史涨停板块数据

    进度日志：/tmp/backfill-limit-up.log
    """
    background_tasks.add_task(_runBackfillLimitUp, startDate, endDate)
    return {
        "status": "started",
        "startDate": startDate,
        "endDate": endDate,
        "logFile": "/tmp/backfill-limit-up.log",
    }
