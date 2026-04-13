from app.database import SessionLocal
from app.services.quant_backtest_service import runBacktest
from app.utils.logger import setupLogger

logger = setupLogger("task_run_backtest")


def runQuantBacktest(runId: str | None = None) -> dict:
    """
    执行量化回测任务。

    runId: 批次标识，默认按当前年份生成，如 '2025_full'
    """
    if not runId:
        from datetime import date
        runId = f"{date.today().year}_full"

    db = SessionLocal()
    try:
        logger.info(f"开始执行量化回测 runId={runId}")
        summary = runBacktest(db, runId)
        logger.info(
            f"量化回测完成 runId={runId} 交易次数={summary['total']} "
            f"胜率={summary['winRate']}% 均收益={summary['avgReturn']}%"
        )
        return summary
    except Exception as e:
        logger.error(f"量化回测任务异常 runId={runId} 错误={e}", exc_info=True)
        raise
    finally:
        db.close()
