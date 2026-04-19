import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

SHANGHAI_TZ = "Asia/Shanghai"

from app.tasks.fetch_quotes import runFetchQuotes
from app.tasks.detect_signals import runDetectSignals, runSendNotifications
from app.tasks.fetch_heat import runFetchHeat
from app.tasks.fetch_morning_brief import runFetchMorningBrief
from app.tasks.summarize_morning_brief import runSummarizeMorningBrief
from app.tasks.daily_prediction import runDailyPrediction
from app.tasks.verify_predictions import runVerifyPredictions
from app.tasks.fetch_limit_up import runFetchLimitUp
from app.tasks.daily_rule_review import runDailyRuleReview
from app.utils.logger import setupLogger

logger = setupLogger("scheduler")

scheduler = BackgroundScheduler()


def _notifyOpenClaw(taskName: str, error: str) -> None:
    """发送任务失败通知到 OpenClaw webhook"""
    token = os.environ.get("OPENCLAW_HOOKS_TOKEN")
    url = os.environ.get("OPENCLAW_HOOKS_URL")
    if not token or not url:
        return
    try:
        requests.post(
            url,
            json={"text": f"【quant任务失败】{taskName}: {error}", "mode": "now"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
    except Exception:
        pass


def initScheduler() -> None:
    """初始化定时任务调度器"""

    # 每个交易日08:30采集盘前纪要
    scheduler.add_job(
        _runFetchMorningBrief,
        trigger=CronTrigger(hour=8, minute=30, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="fetch_morning_brief",
        name="采集盘前纪要",
        replace_existing=True,
    )

    # 每个交易日08:35生成盘前纪要 AI 摘要（采集完后5分钟兜底，防止采集耗时较长）
    scheduler.add_job(
        _runSummarizeMorningBrief,
        trigger=CronTrigger(hour=8, minute=35, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="summarize_morning_brief",
        name="生成盘前摘要",
        replace_existing=True,
    )

    # 每个交易日09:05采集涨停板块数据
    scheduler.add_job(
        _runFetchLimitUp,
        trigger=CronTrigger(hour=9, minute=5, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="fetch_limit_up",
        name="采集涨停板块",
        replace_existing=True,
    )

    # 每个交易日09:08验证昨日预测
    scheduler.add_job(
        _runVerifyPredictions,
        trigger=CronTrigger(hour=9, minute=8, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="verify_predictions",
        name="验证昨日预测",
        replace_existing=True,
    )

    # 每个交易日09:10规则复盘（验证完成后分析30天滚动数据）
    scheduler.add_job(
        _runDailyRuleReview,
        trigger=CronTrigger(hour=9, minute=10, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="daily_rule_review",
        name="规则复盘分析",
        replace_existing=True,
    )


    # 每个交易日09:30执行每日预测打分
    scheduler.add_job(
        _runDailyPrediction,
        trigger=CronTrigger(hour=9, minute=30, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="daily_prediction",
        name="每日预测打分",
        replace_existing=True,
    )

    # 每个交易日15:30（北京时间）拉取股票热度数据
    scheduler.add_job(
        _runFetchHeat,
        trigger=CronTrigger(hour=15, minute=30, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="fetch_stock_heat",
        name="拉取股票热度",
        replace_existing=True,
    )

    # 每个交易日16:00拉取行情数据
    scheduler.add_job(
        _runFetchQuotes,
        trigger=CronTrigger(hour=16, minute=0, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="fetch_daily_quotes",
        name="拉取日线行情",
        replace_existing=True,
    )

    # 每个交易日16:20计算 EXPMA
    scheduler.add_job(
        _runCalcExpma,
        trigger=CronTrigger(hour=16, minute=20, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="calc_expma",
        name="计算EXPMA均线",
        replace_existing=True,
    )

    # 每个交易日16:30执行信号检测
    scheduler.add_job(
        _runDetectSignals,
        trigger=CronTrigger(hour=16, minute=30, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="detect_signals",
        name="检测突破信号",
        replace_existing=True,
    )

    # 每个交易日16:45推送通知
    scheduler.add_job(
        _runSendNotifications,
        trigger=CronTrigger(hour=16, minute=45, day_of_week="mon-fri", timezone="Asia/Shanghai"),
        id="send_notifications",
        name="推送微信通知",
        replace_existing=True,
    )

    # 每周五17:00计算所有股票周线数据
    scheduler.add_job(
        _runCalcWeekly,
        trigger=CronTrigger(hour=17, minute=0, day_of_week="fri", timezone="Asia/Shanghai"),
        id="calc_weekly",
        name="计算周线数据",
        replace_existing=True,
    )

    # 每周日22:00执行量化回测
    scheduler.add_job(
        _runQuantBacktest,
        trigger=CronTrigger(hour=22, minute=0, day_of_week="sun", timezone="Asia/Shanghai"),
        id="quant_backtest",
        name="量化策略回测",
        replace_existing=True,
    )

    # 每周六10:00（北京时间）同步股票列表
    scheduler.add_job(
        _runSyncStockList,
        trigger=CronTrigger(hour=10, minute=0, day_of_week="sat", timezone="Asia/Shanghai"),
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
        _notifyOpenClaw("同步股票列表", str(e))
    finally:
        db.close()


def _runCalcExpma() -> None:
    """计算EXPMA均线（定时任务包装）"""
    from app.database import SessionLocal
    from app.services.quote_service import calcExpmaForAll

    db = SessionLocal()
    try:
        calcExpmaForAll(db)
    except Exception as e:
        logger.error(f"EXPMA计算任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("计算EXPMA均线", str(e))
    finally:
        db.close()


def _runQuantBacktest() -> None:
    """量化回测（定时任务包装）"""
    from app.tasks.run_backtest import runQuantBacktest

    try:
        runQuantBacktest()
    except Exception as e:
        logger.error(f"量化回测任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("量化策略回测", str(e))


def _runFetchLimitUp() -> None:
    """采集涨停板块数据（定时任务包装）"""
    try:
        runFetchLimitUp()
    except Exception as e:
        logger.error(f"采集涨停板块任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("采集涨停板块", str(e))


def _runCalcWeekly() -> None:
    """计算周线数据（定时任务包装）"""
    from app.database import SessionLocal
    from app.services.quote_service import calcWeeklyForAll

    db = SessionLocal()
    try:
        calcWeeklyForAll(db)
    except Exception as e:
        logger.error(f"周线计算任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("计算周线数据", str(e))
    finally:
        db.close()


def _runFetchMorningBrief() -> None:
    """采集盘前纪要（定时任务包装）"""
    try:
        runFetchMorningBrief()
    except Exception as e:
        logger.error(f"采集盘前纪要任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("采集盘前纪要", str(e))


def _runSummarizeMorningBrief() -> None:
    """生成盘前摘要（定时任务包装）"""
    try:
        runSummarizeMorningBrief()
    except Exception as e:
        logger.error(f"生成盘前摘要任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("生成盘前摘要", str(e))


def _runVerifyPredictions() -> None:
    """验证昨日预测（定时任务包装）"""
    try:
        runVerifyPredictions()
    except Exception as e:
        logger.error(f"验证昨日预测任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("验证昨日预测", str(e))


def _runDailyRuleReview() -> None:
    """规则复盘分析（定时任务包装）"""
    try:
        runDailyRuleReview()
    except Exception as e:
        logger.error(f"规则复盘分析任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("规则复盘分析", str(e))


def _runDailyPrediction() -> None:
    """每日预测打分（定时任务包装）"""
    try:
        runDailyPrediction()
    except Exception as e:
        logger.error(f"每日预测打分任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("每日预测打分", str(e))


def _runFetchHeat() -> None:
    """拉取股票热度（定时任务包装）"""
    try:
        runFetchHeat()
    except Exception as e:
        logger.error(f"拉取股票热度任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("拉取股票热度", str(e))


def _runFetchQuotes() -> None:
    """拉取日线行情（定时任务包装）"""
    try:
        runFetchQuotes()
    except Exception as e:
        logger.error(f"拉取日线行情任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("拉取日线行情", str(e))


def _runDetectSignals() -> None:
    """检测突破信号（定时任务包装）"""
    try:
        runDetectSignals()
    except Exception as e:
        logger.error(f"检测突破信号任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("检测突破信号", str(e))


def _runSendNotifications() -> None:
    """推送微信通知（定时任务包装）"""
    try:
        runSendNotifications()
    except Exception as e:
        logger.error(f"推送微信通知任务异常 错误={e}", exc_info=True)
        _notifyOpenClaw("推送微信通知", str(e))
