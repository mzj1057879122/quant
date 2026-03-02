from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import getDb
from app.tasks.scheduler import getSchedulerStatus
from app.tasks.fetch_quotes import runFetchQuotes
from app.tasks.detect_signals import runDetectSignals, runSendNotifications

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
