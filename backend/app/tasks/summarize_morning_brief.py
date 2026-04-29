import os
import subprocess
from datetime import date
from pathlib import Path

from app.database import SessionLocal
from app.models.morning_brief import MorningBrief
from app.utils.logger import setupLogger

logger = setupLogger("task_summarize_morning_brief")

SUMMARIZE_PROMPT_TEMPLATE = """你是A股盘前分析助手。请从以下盘前纪要中提取最重要的信息，输出格式严格如下：

## 今日主线
（1-3个最强板块，每个格式：**板块名**：核心催化剂一句话）

## 重点个股
（3-5只最值得关注的，格式：代码+名称：理由一句话）

## 市场情绪
（一句话：今日整体环境判断，如"情绪偏强，算力主线延续"）

## 风险提示
（如有，一句话；没有则省略此项）

要求：言简意赅，全文不超过300字，中文输出。

---
{content}
"""

CLAUDE_BIN = "/home/zejianma/.nvm/versions/node/v24.13.0/bin/claude"


def _buildEnv() -> dict:
    """构建包含 ANTHROPIC 认证的环境变量字典，优先读 .env 文件。"""
    env = dict(os.environ)

    # 尝试从 .env 文件读取（覆盖）
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    env[key] = val

    return env


def _callClaude(prompt: str) -> str | None:
    try:
        env = _buildEnv()
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--max-turns", "1", "--permission-mode", "bypassPermissions"],
            capture_output=True, text=True, timeout=90, env=env
        )
        if result.returncode != 0:
            logger.error(f"Claude CLI 调用失败 returncode={result.returncode} stderr={result.stderr[:500]}")
            return None
        output = result.stdout.strip()
        return output if output else None
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI 调用超时")
        return None
    except Exception as e:
        logger.error(f"Claude CLI 调用异常 错误={e}", exc_info=True)
        return None


def runSummarizeMorningBrief(targetDate: date | None = None) -> None:
    """
    对盘前纪要生成 AI 浓缩摘要，写入 morning_brief.ai_summary。
    briefA 和 briefB 合并后生成一条摘要，写入当天最新的记录（先 briefA，没有则 briefB）。
    """
    today = targetDate or date.today()
    db = SessionLocal()
    try:
        briefs = db.query(MorningBrief).filter(
            MorningBrief.briefDate == today
        ).all()

        if not briefs:
            logger.info(f"当日无盘前纪要，跳过摘要生成 date={today}")
            return

        # 拼合有效 rawContent
        contents = []
        for b in briefs:
            if b.rawContent and len(b.rawContent) >= 200:
                label = "【纪要A】" if b.source == "briefA" else "【纪要B】"
                contents.append(f"{label}\n{b.rawContent[:3000]}")

        if not contents:
            logger.info(f"当日纪要内容为空，跳过摘要生成 date={today}")
            return

        combined = "\n\n".join(contents)
        prompt = SUMMARIZE_PROMPT_TEMPLATE.format(content=combined)

        logger.info(f"开始生成盘前摘要 date={today} sources={[b.source for b in briefs]}")
        summary = _callClaude(prompt)

        if not summary:
            logger.error(f"AI 摘要生成失败 date={today}")
            return

        # 优先写入 briefA，没有则写 briefB
        target = next((b for b in briefs if b.source == "briefA"), briefs[0])
        target.aiSummary = summary
        db.commit()

        logger.info(f"盘前摘要写入成功 date={today} source={target.source} len={len(summary)}")

    except Exception as e:
        logger.error(f"盘前摘要生成任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
