from datetime import date
from itertools import groupby
from operator import attrgetter

import httpx

from app.models.signal import Signal
from app.config import settings
from app.utils.logger import setupLogger

logger = setupLogger("notify_service")

# 信号类型中文映射
SIGNAL_TYPE_NAMES = {
    "approaching": "接近前高",
    "breakout": "突破前高",
    "failed": "突破失败",
    # 旧类型兼容
    "breakout_confirm": "突破确认",
    "false_breakout": "假突破",
    "breakdown": "突破失败下跌",
}


async def sendServerChan(title: str, content: str) -> bool:
    """通过Server酱推送消息到微信"""
    sendKey = settings.serverChanKey
    if not sendKey:
        logger.error("Server酱SendKey未配置，无法推送", exc_info=False)
        return False

    url = f"https://sctapi.ftqq.com/{sendKey}.send"
    data = {"title": title, "desp": content}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data, timeout=10)
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"推送成功 title={title}")
                return True
            else:
                logger.error(
                    f"推送失败 title={title} response={result}",
                    exc_info=True,
                )
                return False
    except Exception as e:
        logger.error(f"推送异常 title={title} 错误={e}", exc_info=True)
        return False


def formatDailyReport(signals: list[Signal], reportDate: date) -> tuple[str, str]:
    """
    格式化每日信号汇报
    返回 (标题, 内容Markdown)
    """
    dateStr = reportDate.strftime("%m-%d")
    title = f"量化监控 {dateStr} 共{len(signals)}条信号"

    lines = [
        f"## 量化股票监控 - 每日信号汇报",
        f"",
        f"**日期**：{reportDate.strftime('%Y-%m-%d')}",
        f"",
    ]

    # 按信号类型分组
    sortedSignals = sorted(signals, key=attrgetter("signalType"))
    for signalType, group in groupby(sortedSignals, key=attrgetter("signalType")):
        groupList = list(group)
        typeName = SIGNAL_TYPE_NAMES.get(signalType, signalType)
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"### {typeName} ({len(groupList)}条)")
        lines.append(f"")
        lines.append(f"| 股票 | 前高价 | 收盘价 |")
        lines.append(f"|------|--------|--------|")

        for s in groupList:
            lines.append(
                f"| {s.stockCode} {s.stockName} | {s.previousHighPrice} | {s.closePrice} |"
            )

        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"> 以上信号由量化监控系统自动生成，仅供参考")

    content = "\n".join(lines)
    return title, content


async def sendDailyNotification(signals: list[Signal], reportDate: date | None = None) -> bool:
    """发送每日汇总通知"""
    if not signals:
        logger.info("无信号需要推送")
        return True

    if reportDate is None:
        reportDate = signals[0].signalDate

    title, content = formatDailyReport(signals, reportDate)
    success = await sendServerChan(title, content)

    if not success:
        # 失败重试一次
        logger.info("推送失败，30秒后重试")
        import asyncio
        await asyncio.sleep(30)
        success = await sendServerChan(title, content)

    return success
