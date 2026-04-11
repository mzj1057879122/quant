"""
采集韭研公社涨停板块数据
访问 https://www.jiuyangongshe.com/action/{date}，拦截 /api/v1/action/field 接口响应
"""
import json
from datetime import date as date_type
from typing import Optional

from app.database import SessionLocal
from app.models.limit_up_plate import LimitUpPlate
from app.utils.logger import setupLogger

logger = setupLogger("fetch_limit_up")

JIUYAN_COOKIE = (
    "SESSION=NDI4YWJhM2UtNDM4Yi00YjU2LWJjNzgtNGFiNDdiYWMxYzhl; "
    "Hm_lvt_58aa18061df7855800f2a1b32d6da7f4=1774598692,1774855487,1775547199,1775723406; "
    "Hm_lpvt_58aa18061df7855800f2a1b32d6da7f4=1775909707"
)

JIUYAN_URL = "https://www.jiuyangongshe.com/action/{date}"
FIELD_API_PATH = "/api/v1/action/field"


def _stripPrefix(code: str) -> str:
    """去掉 sh/sz 前缀，只保留6位数字代码"""
    code = code.strip()
    if code.lower().startswith(("sh", "sz", "bj")):
        return code[2:]
    return code


def _fetchFieldData(date_str: str) -> Optional[dict]:
    """用 Playwright 访问页面并拦截 field API 响应，返回 JSON 数据"""
    from playwright.sync_api import sync_playwright

    result_data = {}

    def _handleResponse(response):
        if FIELD_API_PATH in response.url:
            try:
                result_data["body"] = response.json()
            except Exception as e:
                logger.error(f"解析 field API 响应失败 url={response.url} 错误={e}", exc_info=True)

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
                "value": "1774598692,1774855487,1775547199,1775723406",
                "domain": ".jiuyangongshe.com",
                "path": "/",
            },
            {
                "name": "Hm_lpvt_58aa18061df7855800f2a1b32d6da7f4",
                "value": "1775909707",
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

        # 点击"全部异动解析"按钮
        try:
            btn = page.locator("text=全部异动解析").first
            if btn.count() > 0:
                btn.click()
                logger.info("已点击「全部异动解析」")
            else:
                logger.info("未找到「全部异动解析」按钮，继续等待")
        except Exception as e:
            logger.error(f"点击「全部异动解析」失败 错误={e}", exc_info=True)

        page.wait_for_timeout(3000)

        # 如果响应拦截未触发，尝试直接请求 API
        if not result_data:
            logger.info("响应拦截未获取到数据，尝试直接请求 API")
            try:
                api_url = f"https://www.jiuyangongshe.com{FIELD_API_PATH}?date={date_str}"
                api_response = page.request.get(api_url)
                result_data["body"] = api_response.json()
            except Exception as e:
                logger.error(f"直接请求 API 失败 错误={e}", exc_info=True)

        browser.close()

    return result_data.get("body")


def _parseAndSave(data: dict, date_str: str, db) -> tuple[int, int]:
    """解析 API 响应并写入数据库，返回 (plates_count, stocks_count)"""
    trade_date = date_type.fromisoformat(date_str)

    # 响应结构示例：
    # { "data": { "list": [ { "name": "板块名", "stocks": [ {...}, ... ] } ] } }
    plates_list = []
    try:
        resp_data = data.get("data") or data
        if isinstance(resp_data, dict):
            plates_list = resp_data.get("list") or resp_data.get("plates") or []
        elif isinstance(resp_data, list):
            plates_list = resp_data
    except Exception as e:
        logger.error(f"解析响应结构失败 错误={e} data={json.dumps(data)[:500]}", exc_info=True)
        return 0, 0

    if not plates_list:
        logger.error(f"未找到板块数据，响应结构：{json.dumps(data)[:500]}")
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
            reason = (
                stock.get("reason")
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
                db.merge(record) if False else db.add(record)
                db.flush()
                stocks_count += 1
            except Exception:
                db.rollback()

    db.commit()
    return plates_count, stocks_count


def runFetchLimitUp(date_str: str = None) -> dict:
    """
    采集韭研公社涨停板块数据

    Args:
        date_str: 日期字符串，格式 '2026-04-10'，默认今天

    Returns:
        {'success': True/False, 'date': ..., 'plates': N, 'stocks': N}
    """
    if date_str is None:
        date_str = date_type.today().isoformat()

    logger.info(f"开始采集涨停板块数据 date={date_str}")

    try:
        data = _fetchFieldData(date_str)
        if not data:
            logger.error(f"未获取到涨停板块数据 date={date_str}")
            return {"success": False, "date": date_str, "plates": 0, "stocks": 0, "error": "未获取到数据"}

        db = SessionLocal()
        try:
            plates_count, stocks_count = _parseAndSave(data, date_str, db)
        finally:
            db.close()

        logger.info(f"涨停板块采集完成 date={date_str} plates={plates_count} stocks={stocks_count}")
        return {"success": True, "date": date_str, "plates": plates_count, "stocks": stocks_count}

    except Exception as e:
        logger.error(f"采集涨停板块数据异常 date={date_str} 错误={e}", exc_info=True)
        return {"success": False, "date": date_str, "plates": 0, "stocks": 0, "error": str(e)}
