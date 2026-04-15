"""
daily_rule_review.py
每日规则复盘：验证完成后用滚动30天数据分析预测质量。
发现异常 → Claude生成代码改动 → 写回daily_prediction.py → commit → 重启后端。
触发时机：每个交易日 09:10
"""
import json
import subprocess
import os
import re
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
ALERT_THRESHOLD = 0.40
CRITICAL_THRESHOLD = 0.30

PREDICTION_FILE = os.path.join(os.path.dirname(__file__), "daily_prediction.py")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))


def runDailyRuleReview() -> None:
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        windowStart = today - timedelta(days=WINDOW_DAYS)
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

        byConf: dict[str, list] = defaultdict(list)
        byPred: dict[str, list] = defaultdict(list)
        bySignal: dict[str, list] = defaultdict(list)
        SIGNAL_KEYS = ["放量突破", "缩量", "极值量", "板块退潮", "锁仓", "无明显信号"]

        for r in rows:
            if r.confidence:
                byConf[r.confidence].append(r.isCorrect)
            if r.prediction:
                byPred[r.prediction].append(r.isCorrect)
            sig = r.technicalSignal or ""
            matched = False
            for key in SIGNAL_KEYS:
                if key in sig:
                    bySignal[key].append(r.isCorrect)
                    matched = True
            if not matched:
                bySignal["其他"].append(r.isCorrect)

        def calcStats(groups):
            return {
                k: {"total": len(v), "correct": sum(v), "rate": round(sum(v)/len(v)*100, 1) if v else 0}
                for k, v in groups.items() if len(v) >= 3
            }

        confStats = calcStats(byConf)
        predStats = calcStats(byPred)
        signalStats = calcStats(bySignal)

        alertLevel = "none"
        anomalies = []

        for key, stat in {**confStats, **predStats, **signalStats}.items():
            rate = stat["rate"] / 100
            if stat["total"] >= 5:
                if rate < CRITICAL_THRESHOLD:
                    alertLevel = "critical"
                    anomalies.append(f"【严重】「{key}」近{WINDOW_DAYS}天胜率仅{stat['rate']}%（{stat['correct']}/{stat['total']}）")
                elif rate < ALERT_THRESHOLD and alertLevel != "critical":
                    alertLevel = "warn"
                    anomalies.append(f"【偏低】「{key}」近{WINDOW_DAYS}天胜率{stat['rate']}%（{stat['correct']}/{stat['total']}）")

        suggestions = []
        codeChanged = False

        if anomalies:
            suggestions, patch = _askClaudeForPatch(
                anomalies, confStats, predStats, signalStats, overallRate
            )
            if patch:
                codeChanged = _applyPatch(patch, today)

        # 写DB
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

        if codeChanged:
            logger.info(f"规则已自动升级并重启 date={today}")
        logger.info(f"规则复盘完成 date={today} total={total} rate={overallRate:.1%} alert={alertLevel} codeChanged={codeChanged}")

    except Exception as e:
        db.rollback()
        logger.error(f"规则复盘任务异常 错误={e}", exc_info=True)
    finally:
        db.close()


def _askClaudeForPatch(anomalies, confStats, predStats, signalStats, overallRate):
    """
    调用Claude分析异常，返回(suggestions文字列表, patch代码字符串或None)
    patch格式：Claude输出两段，第一段是文字建议，第二段是```python...```代码块，
    包含对daily_prediction.py中某个函数或参数的具体修改。
    """
    with open(PREDICTION_FILE, "r") as f:
        currentCode = f.read()

    prompt = f"""你是A股短线交易预测系统的规则优化顾问。

当前预测代码（daily_prediction.py）：
```python
{currentCode}
```

近{WINDOW_DAYS}天验证数据：
- 整体胜率：{overallRate:.1%}
- 发现异常：
{chr(10).join(anomalies)}
- 置信度分组：{json.dumps(confStats, ensure_ascii=False)}
- 预测方向分组：{json.dumps(predStats, ensure_ascii=False)}
- 信号类型分组：{json.dumps(signalStats, ensure_ascii=False)}

请：
1. 给出1-2条文字建议（每条以"- 【建议】"开头）
2. 给出对应的代码修改（只改参数值或判断阈值，不改逻辑结构），用```python```包裹，输出修改后的完整函数或修改后的相关代码段，并在注释中说明改动原因和日期（{today_str()}）

规则：
- 只修改数值参数（如分值阈值、倍数、天数），不重写逻辑结构
- 如果数据量不足以得出可靠结论，就不输出代码块，只输出文字建议
- 每次最多改1-2个参数，改动幅度不超过原值的30%
- 直接输出，不需要人工确认，系统会自动应用

只输出建议+代码，不要废话。"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "claude-sonnet-4-6", "--max-turns", "1"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0 or not result.stdout.strip():
            return [], None

        output = result.stdout.strip()

        # 提取文字建议
        suggestions = [l.strip() for l in output.splitlines() if l.strip().startswith("- 【建议】")]

        # 提取代码块
        codeMatch = re.search(r"```python\s*(.*?)```", output, re.DOTALL)
        patch = codeMatch.group(1).strip() if codeMatch else None

        return suggestions, patch

    except Exception as e:
        logger.warning(f"Claude分析失败 错误={e}")
        return [], None


def _applyPatch(patch: str, today: date) -> bool:
    """
    将patch应用到daily_prediction.py：
    - patch是修改后的某个函数/代码段
    - 通过函数名匹配找到原函数，整体替换
    - commit + 重启后端
    """
    try:
        with open(PREDICTION_FILE, "r") as f:
            original = f.read()

        # 提取patch中的函数名
        funcMatch = re.search(r"^def (\w+)\(", patch, re.MULTILINE)
        if not funcMatch:
            logger.warning("patch中未找到函数定义，跳过应用")
            return False

        funcName = funcMatch.group(1)

        # 在原文件中找到对应函数
        pattern = rf"(^def {re.escape(funcName)}\(.*?)(?=\n^def |\Z)"
        origMatch = re.search(pattern, original, re.MULTILINE | re.DOTALL)
        if not origMatch:
            logger.warning(f"原文件中未找到函数 {funcName}，跳过应用")
            return False

        newCode = original[:origMatch.start()] + patch + "\n\n" + original[origMatch.end():]

        # 语法检查
        try:
            compile(newCode, PREDICTION_FILE, "exec")
        except SyntaxError as e:
            logger.error(f"patch语法错误，放弃应用 错误={e}")
            return False

        # 写回文件
        with open(PREDICTION_FILE, "w") as f:
            f.write(newCode)

        # git commit
        commitMsg = f"auto: rule_review自动升级预测规则 date={today}"
        subprocess.run(
            ["git", "add", "backend/app/tasks/daily_prediction.py"],
            cwd=PROJECT_ROOT, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", commitMsg],
            cwd=PROJECT_ROOT, capture_output=True
        )
        logger.info(f"规则代码已更新并commit funcName={funcName}")

        # 重启后端（发信号给uvicorn reload）
        subprocess.Popen(
            ["bash", os.path.join(PROJECT_ROOT, "run.sh"), "restart"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info("后端重启信号已发送")
        return True

    except Exception as e:
        logger.error(f"应用patch失败 错误={e}", exc_info=True)
        return False


def today_str():
    return date.today().isoformat()
