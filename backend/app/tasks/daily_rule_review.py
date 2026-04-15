"""
daily_rule_review.py
每日规则复盘：验证完成后用滚动30天数据分析预测质量，发现异常规律存DB。
触发时机：每个交易日 09:10（verify_predictions完成后）
"""
import json
import subprocess
from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.backtest_result import BacktestResult
from app.models.rule_review import RuleReview
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_daily_rule_review")

WINDOW_DAYS = 30
ALERT_THRESHOLD = 0.40   # 某维度胜率低于40%触发warn
CRITICAL_THRESHOLD = 0.30  # 低于30%触发critical


def runDailyRuleReview() -> None:
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        windowStart = today - timedelta(days=WINDOW_DAYS)

        # 拉最近30天已验证的预测
        rows = db.execute(
            select(BacktestResult).where(
                BacktestResult.predictDate >= windowStart,
                BacktestResult.predictDate < today,
                BacktestResult.isCorrect.isnot(None),
            )
        ).scalars().all()

        if len(rows) < 10:
            logger.info(f"样本不足跳过 count={len(rows)}")
            return

        total = len(rows)
        correct = sum(1 for r in rows if r.isCorrect == 1)
        overallRate = correct / total

        # 按置信度分组
        byConf: dict[str, list] = defaultdict(list)
        for r in rows:
            if r.confidence:
                byConf[r.confidence].append(r.isCorrect)

        # 按预测方向分组
        byPred: dict[str, list] = defaultdict(list)
        for r in rows:
            if r.prediction:
                byPred[r.prediction].append(r.isCorrect)

        # 按信号关键词分组（粗粒度）
        bySignal: dict[str, list] = defaultdict(list)
        SIGNAL_KEYS = ["放量突破", "缩量", "极值量", "板块退潮", "锁仓", "无明显信号"]
        for r in rows:
            sig = r.technicalSignal or ""
            matched = False
            for key in SIGNAL_KEYS:
                if key in sig:
                    bySignal[key].append(r.isCorrect)
                    matched = True
            if not matched:
                bySignal["其他"].append(r.isCorrect)

        def calcStats(groups: dict) -> dict:
            return {
                k: {
                    "total": len(v),
                    "correct": sum(v),
                    "rate": round(sum(v) / len(v) * 100, 1) if v else 0,
                }
                for k, v in groups.items() if len(v) >= 3
            }

        confStats = calcStats(byConf)
        predStats = calcStats(byPred)
        signalStats = calcStats(bySignal)

        # 判断告警等级
        alertLevel = "none"
        anomalies = []
        suggestions = []

        for key, stat in {**confStats, **predStats, **signalStats}.items():
            rate = stat["rate"] / 100
            if stat["total"] >= 5:
                if rate < CRITICAL_THRESHOLD:
                    alertLevel = "critical"
                    anomalies.append(f"【严重】「{key}」近{WINDOW_DAYS}天胜率仅{stat['rate']}%（{stat['correct']}/{stat['total']}）")
                elif rate < ALERT_THRESHOLD and alertLevel != "critical":
                    alertLevel = "warn"
                    anomalies.append(f"【偏低】「{key}」近{WINDOW_DAYS}天胜率{stat['rate']}%（{stat['correct']}/{stat['total']}）")

        # 有异常时调用Claude分析
        if anomalies:
            suggestions = _askClaude(anomalies, confStats, predStats, signalStats, overallRate)

        # 写入DB（覆盖当天的记录）
        existing = db.execute(
            select(RuleReview).where(RuleReview.reviewDate == today)
        ).scalar_one_or_none()

        record = existing or RuleReview(reviewDate=today)
        record.windowDays = WINDOW_DAYS
        record.totalPredictions = total
        record.overallWinRate = round(overallRate * 100, 2)
        record.bySignalType = json.dumps(signalStats, ensure_ascii=False)
        record.byConfidence = json.dumps(confStats, ensure_ascii=False)
        record.byPrediction = json.dumps(predStats, ensure_ascii=False)
        record.anomalies = "\n".join(anomalies) if anomalies else None
        record.suggestions = "\n".join(suggestions) if suggestions else None
        record.alertLevel = alertLevel

        if not existing:
            db.add(record)
        db.commit()

        logger.info(f"规则复盘完成 date={today} total={total} rate={overallRate:.1%} alert={alertLevel}")

        if alertLevel in ("warn", "critical"):
            logger.warning(f"规则异常告警 anomalies={anomalies}")

    except Exception as e:
        db.rollback()
        logger.error(f"规则复盘任务异常 错误={e}", exc_info=True)
    finally:
        db.close()


def _askClaude(anomalies, confStats, predStats, signalStats, overallRate) -> list[str]:
    """调用Claude分析异常，返回规则修订建议列表"""
    prompt = f"""你是A股短线交易系统的规则优化顾问。

当前预测系统整体胜率：{overallRate:.1%}

发现以下异常：
{chr(10).join(anomalies)}

各维度详情：
置信度分组：{json.dumps(confStats, ensure_ascii=False)}
预测方向分组：{json.dumps(predStats, ensure_ascii=False)}
信号类型分组：{json.dumps(signalStats, ensure_ascii=False)}

请给出2-3条具体的规则修订建议，格式：
- 【建议X】具体改什么，为什么

只输出建议，不要废话。"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "claude-haiku-4-5", "--max-turns", "1"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip().startswith("- ")]
            return lines[:3] if lines else [result.stdout.strip()[:200]]
    except Exception as e:
        logger.warning(f"Claude分析失败 错误={e}")
    return []
