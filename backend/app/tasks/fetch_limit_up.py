"""
采集韭研公社涨停板块数据
访问 https://www.jiuyangongshe.com/action/{date}，拦截以下 API 响应：
  - /api/v1/action/field      → 涨停板块列表（板块名 + 股票列表）
  - /api/v1/action/diagram-url → 每日涨停简图 OSS 地址
页面渲染完成后，提取 .transaction-box.yd-box 区块内的利好详情，UPDATE 到 reason 字段
"""
import json
import re
from datetime import date as date_type
from typing import Optional

from sqlalchemy import text

from app.database import SessionLocal
from app.models.limit_up_plate import LimitUpPlate
from app.models.limit_up_diagram import LimitUpDiagram
from app.utils.logger import setupLogger

logger = setupLogger("fetch_limit_up")

JIUYAN_URL = "https://www.jiuyangongshe.com/action/{date}"
FIELD_API_PATH = "/api/v1/action/field"
DIAGRAM_API_PATH = "/api/v1/action/diagram-url"


def _stripPrefix(code: str) -> str:
    """去掉 sh/sz 前缀，只保留6位数字代码"""
    code = code.strip()
    if code.lower().startswith(("sh", "sz", "bj")):
        return code[2:]
    return code


def _cleanReason(text: str) -> str:
    """
    清理利好文本：去除「...展开」「展开全文」等末尾截断提示
    """
    if not text:
        return text
    # 去掉末尾的 ...展开 / 展开 / ...查看更多 等
    text = re.sub(r'[.…]+展开\s*$', '', text.strip())
    text = re.sub(r'展开全文\s*$', '', text.strip())
    text = re.sub(r'查看更多\s*$', '', text.strip())
    return text.strip()


def _fetchPageData(date_str: str) -> dict:
    """
    用 Playwright 访问页面，同时：
    1. 拦截 field API 响应 → 板块列表数据
    2. 拦截 diagram-url API 响应 → 简图 URL
    3. 提取页面上 .transaction-box.yd-box 区块 → 股票利好详情

    Returns:
        {
            "field": <dict>,        # field API 响应体
            "diagramUrl": <str>,    # 简图 URL，可能为 None
            "details": {            # 股票代码 → 利好详情文本
                "600743": "...",
            }
        }
    """
    from playwright.sync_api import sync_playwright

    field_data: dict = {}
    diagram_url: list = [None]  # 用 list 以便闭包内赋值

    def _handleResponse(response):
        if FIELD_API_PATH in response.url:
            try:
                field_data["body"] = response.json()
            except Exception as e:
                logger.error(f"解析 field API 响应失败 url={response.url} 错误={e}", exc_info=True)
        elif DIAGRAM_API_PATH in response.url:
            try:
                resp = response.json()
                url_val = resp.get("data") or resp.get("url") or resp.get("diagramUrl")
                if url_val:
                    diagram_url[0] = str(url_val)
                    logger.info(f"拦截到简图URL: {diagram_url[0]}")
            except Exception as e:
                logger.error(f"解析 diagram-url API 响应失败 url={response.url} 错误={e}", exc_info=True)

    details: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # 注入 SESSION cookie
        context.add_cookies([
            {
                "name": "SESSION",
                "value": "NDI4YWJhM2UtNDM4Yi00YjU2LWJjNzgtNGFiNDdiYWMxYzhl",
                "domain": ".jiuyangongshe.com",
                "path": "/",
            },
            {
                "name": "Hm_lvt_58aa18061df7855800f2a1b32d6da7f4",
                "value": "1775723406,1776070948,1776926136,1777275237",
                "domain": ".jiuyangongshe.com",
                "path": "/",
            },
            {
                "name": "Hm_lpvt_58aa18061df7855800f2a1b32d6da7f4",
                "value": "1777347357",
                "domain": ".jiuyangongshe.com",
                "path": "/",
            },
        ])

        page = context.new_page()
        page.on("response", _handleResponse)

        url = JIUYAN_URL.format(date=date_str)
        logger.info(f"访问页面 url={url}")
        page.goto(url, timeout=30000)
        page.wait_for_timeout(4000)

        # 点击"全部异动解析"按钮，触发详情加载
        try:
            btn = page.locator("text=全部异动解析").first
            if btn.count() > 0:
                btn.click()
                logger.info("已点击「全部异动解析」")
            else:
                logger.info("未找到「全部异动解析」按钮，继续")
        except Exception as e:
            logger.error(f"点击「全部异动解析」失败 错误={e}", exc_info=True)

        page.wait_for_timeout(4000)

        # 如果 field 响应拦截未触发，直接请求 API
        if not field_data:
            logger.info("响应拦截未获取到 field 数据，尝试直接请求 API")
            try:
                api_url = f"https://www.jiuyangongshe.com{FIELD_API_PATH}?date={date_str}"
                api_response = page.request.get(api_url)
                field_data["body"] = api_response.json()
            except Exception as e:
                logger.error(f"直接请求 field API 失败 错误={e}", exc_info=True)

        # 提取页面上每只股票的利好详情
        try:
            boxes = page.query_selector_all("div.transaction-box.yd-box")
            logger.info(f"找到 {len(boxes)} 个 .transaction-box.yd-box 区块")
            for box in boxes:
                # 尝试从区块内文字中匹配 6 位股票代码（或 sh/sz 前缀格式）
                box_text = box.inner_text() or ""
                # 先找 data-code 或 data-stock 属性
                code = None
                try:
                    code_attr = box.get_attribute("data-code") or box.get_attribute("data-stock")
                    if code_attr:
                        code = _stripPrefix(code_attr)
                except Exception:
                    pass

                # 从文本中提取 sh/sz + 6位 格式
                if not code:
                    m = re.search(r'\b(sh|sz|SH|SZ)(\d{6})\b', box_text)
                    if m:
                        code = m.group(2)

                # 也尝试从子元素 span/div 里找
                if not code:
                    try:
                        spans = box.query_selector_all("span, div")
                        for span in spans:
                            span_text = span.inner_text() or ""
                            m2 = re.search(r'\b(sh|sz|SH|SZ)(\d{6})\b', span_text)
                            if m2:
                                code = m2.group(2)
                                break
                            # 纯6位数字也接受
                            m3 = re.search(r'\b(\d{6})\b', span_text)
                            if m3:
                                code = m3.group(1)
                                break
                    except Exception:
                        pass

                if code and box_text:
                    cleaned = _cleanReason(box_text)
                    if cleaned:
                        details[code] = cleaned
        except Exception as e:
            logger.error(f"提取利好详情区块失败 错误={e}", exc_info=True)

        browser.close()

    return {
        "field": field_data.get("body"),
        "diagramUrl": diagram_url[0],
        "details": details,
    }


def _saveDiagramUrl(date_str: str, diagram_url: str, db) -> None:
    """INSERT IGNORE 写入简图URL"""
    trade_date = date_type.fromisoformat(date_str)
    existing = db.query(LimitUpDiagram).filter(LimitUpDiagram.tradeDate == trade_date).first()
    if existing:
        logger.info(f"简图URL已存在，跳过 date={date_str}")
        return
    record = LimitUpDiagram(tradeDate=trade_date, diagramUrl=diagram_url)
    db.add(record)
    db.commit()
    logger.info(f"简图URL已写入 date={date_str} url={diagram_url}")


def _parseAndSave(field_data: dict, date_str: str, db) -> tuple[int, int]:
    """解析 field API 响应并写入 limit_up_plate，返回 (plates_count, stocks_count)"""
    trade_date = date_type.fromisoformat(date_str)

    plates_list = []
    try:
        resp_data = field_data.get("data") or field_data
        if isinstance(resp_data, dict):
            plates_list = resp_data.get("list") or resp_data.get("plates") or []
        elif isinstance(resp_data, list):
            plates_list = resp_data
    except Exception as e:
        logger.error(f"解析响应结构失败 错误={e} data={json.dumps(field_data)[:500]}", exc_info=True)
        return 0, 0

    if not plates_list:
        logger.error(f"未找到板块数据，响应结构：{json.dumps(field_data)[:500]}")
        return 0, 0

    plates_count = 0
    stocks_count = 0

    for plate_idx, plate in enumerate(plates_list):
        plate_name = plate.get("name") or plate.get("plateName") or plate.get("title") or f"板块{plate_idx+1}"
        stocks = plate.get("stocks") or plate.get("list") or plate.get("items") or []

        if not stocks:
            continue

        plates_count += 1

        for sort_idx, stock in enumerate(stocks):
            raw_code = (
                stock.get("stockCode")
                or stock.get("code")
                or stock.get("stock_code")
                or ""
            )
            stock_code = _stripPrefix(raw_code)
            if not stock_code:
                continue

            stock_name = (
                stock.get("stockName")
                or stock.get("name")
                or stock.get("stock_name")
                or ""
            )
            limit_up_days = (
                stock.get("limitUpDays")
                or stock.get("limit_up_days")
                or stock.get("days")
                or None
            )
            limit_up_time = (
                stock.get("limitUpTime")
                or stock.get("limit_up_time")
                or stock.get("time")
                or None
            )
            price = stock.get("price") or stock.get("currentPrice") or None
            change_pct = (
                stock.get("changePct")
                or stock.get("change_pct")
                or stock.get("changeRate")
                or None
            )
            action_info = stock.get("article", {}).get("action_info", {}) or {}
            reason = (
                action_info.get("expound")
                or stock.get("reason")
                or stock.get("limitUpReason")
                or stock.get("limit_up_reason")
                or None
            )

            try:
                price_val = float(price) if price is not None else None
                change_val = float(change_pct) if change_pct is not None else None
            except (ValueError, TypeError):
                price_val = None
                change_val = None

            record = LimitUpPlate(
                tradeDate=trade_date,
                plateName=plate_name,
                stockCode=stock_code,
                stockName=stock_name,
                limitUpDays=str(limit_up_days) if limit_up_days else None,
                limitUpTime=str(limit_up_time) if limit_up_time else None,
                price=price_val,
                changePct=change_val,
                reason=reason,
                sortNo=sort_idx,
            )

            try:
                db.add(record)
                db.flush()
                stocks_count += 1
            except Exception:
                db.rollback()

    db.commit()
    return plates_count, stocks_count


def _updateReasons(date_str: str, details: dict[str, str], db) -> int:
    """
    用页面提取的利好详情更新 limit_up_plate.reason 字段
    只更新 reason 为空或内容更长的记录
    Returns: 更新条数
    """
    if not details:
        return 0

    trade_date = date_type.fromisoformat(date_str)
    updated = 0

    for stock_code, reason_text in details.items():
        if not reason_text:
            continue
        rows = (
            db.query(LimitUpPlate)
            .filter(
                LimitUpPlate.tradeDate == trade_date,
                LimitUpPlate.stockCode == stock_code,
            )
            .all()
        )
        for row in rows:
            # 如果页面抓到的内容比已有的更长（或已有为空），则覆盖
            if not row.reason or len(reason_text) > len(row.reason):
                row.reason = reason_text
                updated += 1

    db.commit()
    logger.info(f"利好详情更新完成 date={date_str} updated={updated}")
    return updated


def runFetchLimitUp(date_str: str = None) -> dict:
    """
    采集韭研公社涨停板块数据（含简图URL + 利好详情）

    Args:
        date_str: 日期字符串，格式 '2026-04-10'，默认今天

    Returns:
        {'success': True/False, 'date': ..., 'plates': N, 'stocks': N,
         'diagramUrl': ..., 'reasonsUpdated': N}
    """
    if date_str is None:
        date_str = date_type.today().isoformat()

    logger.info(f"开始采集涨停板块数据 date={date_str}")

    try:
        page_data = _fetchPageData(date_str)

        field_data = page_data.get("field")
        diagram_url = page_data.get("diagramUrl")
        details = page_data.get("details", {})

        if not field_data:
            logger.error(f"未获取到涨停板块数据 date={date_str}")
            return {"success": False, "date": date_str, "plates": 0, "stocks": 0, "error": "未获取到数据"}

        db = SessionLocal()
        try:
            plates_count, stocks_count = _parseAndSave(field_data, date_str, db)
            reasons_updated = 0  # reason 已在 _parseAndSave 中从 expound 字段写入，无需二次更新
            if diagram_url:
                _saveDiagramUrl(date_str, diagram_url, db)
            else:
                logger.info(f"未获取到简图URL date={date_str}")
        finally:
            db.close()

        logger.info(
            f"涨停板块采集完成 date={date_str} "
            f"plates={plates_count} stocks={stocks_count} "
            f"diagramUrl={diagram_url} reasonsUpdated={reasons_updated}"
        )
        return {
            "success": True,
            "date": date_str,
            "plates": plates_count,
            "stocks": stocks_count,
            "diagramUrl": diagram_url,
            "reasonsUpdated": reasons_updated,
        }

    except Exception as e:
        logger.error(f"采集涨停板块数据异常 date={date_str} 错误={e}", exc_info=True)
        return {"success": False, "date": date_str, "plates": 0, "stocks": 0, "error": str(e)}


def backfillLimitUpHistory(startDate: str, endDate: str) -> dict:
    """
    批量补采历史涨停板块数据

    Args:
        startDate: 开始日期 '2025-01-01'
        endDate:   结束日期 '2025-12-31'

    Returns:
        {'success': N, 'failed': N, 'skipped': N, 'failedDates': [...]}
    """
    import time
    import random
    from datetime import date as date_type, timedelta

    # 生成 startDate 到 endDate 之间所有交易日（跳过周六、周日）
    start = date_type.fromisoformat(startDate)
    end = date_type.fromisoformat(endDate)
    allDates = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # 0=周一 … 4=周五
            allDates.append(cur.isoformat())
        cur += timedelta(days=1)

    # 查询数据库中已有的交易日（避免重复采集）
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT DISTINCT DATE_FORMAT(trade_date, '%Y-%m-%d') FROM limit_up_plate")
        ).fetchall()
        existingDates = {r[0] for r in rows}
    finally:
        db.close()

    missingDates = [d for d in allDates if d not in existingDates]
    logger.info(
        f"补采任务启动 startDate={startDate} endDate={endDate} "
        f"交易日总数={len(allDates)} 已有={len(existingDates)} 待补={len(missingDates)}"
    )

    successCount = 0
    failedDates = []

    for idx, dateStr in enumerate(missingDates):
        logger.info(f"[{idx+1}/{len(missingDates)}] 补采 {dateStr}")
        try:
            result = runFetchLimitUp(dateStr)
            if result.get("success"):
                successCount += 1
                logger.info(
                    f"补采成功 date={dateStr} plates={result.get('plates')} stocks={result.get('stocks')}"
                )
            else:
                failedDates.append(dateStr)
                logger.error(f"补采失败 date={dateStr} error={result.get('error')}")
        except Exception as e:
            failedDates.append(dateStr)
            logger.error(f"补采异常 date={dateStr} 错误={e}", exc_info=True)

        # 每次成功后随机等待 3-6 秒防封
        sleepSec = random.uniform(3, 6)
        time.sleep(sleepSec)

    summary = {
        "success": successCount,
        "failed": len(failedDates),
        "skipped": len(allDates) - len(missingDates),
        "failedDates": failedDates,
    }
    logger.info(f"补采任务完成 {summary}")
    return summary


if __name__ == "__main__":
    # 补采 2026-04-10 数据
    result = runFetchLimitUp("2026-04-10")
    print(result)
