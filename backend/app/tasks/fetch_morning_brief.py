from datetime import date

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.morning_brief import MorningBrief
from app.utils.date_helper import isTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_fetch_morning_brief")

SOURCES = {
    "briefA": "https://www.jiuyangongshe.com/u/4df747be1bf143a998171ef03559b517",
    "briefB": "https://www.jiuyangongshe.com/u/97fc2a020e644adb89570e69ae35ec02",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _fetchLatestArticle(source: str, url: str) -> dict | None:
    """抓取用户主页，返回最新文章的日期和内容，失败返回 None"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 找到文章列表中第一篇文章链接
        article_link = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/p/" in href or "/article/" in href:
                article_link = href
                break

        if not article_link:
            # 尝试更宽泛的选择器：带 class 含 article/post 的链接
            for a in soup.select("a[href]"):
                href = a["href"]
                if href.startswith("/") and len(href) > 5:
                    article_link = href
                    break

        if not article_link:
            logger.error(f"未找到文章链接 source={source} url={url}")
            return None

        # 补全为绝对路径
        if article_link.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            article_link = f"{parsed.scheme}://{parsed.netloc}{article_link}"

        # 抓取文章正文
        art_resp = requests.get(article_link, headers=HEADERS, timeout=15)
        art_resp.raise_for_status()
        art_soup = BeautifulSoup(art_resp.text, "html.parser")

        # 提取正文内容（尝试常见选择器）
        content = ""
        for selector in [
            "div.article-text.p_coten#first",
            "div.article-text",
            "div.article-content",
            "div.content",
            "article",
        ]:
            node = art_soup.select_one(selector)
            if node:
                content = node.get_text(separator="\n", strip=True)
                break

        if not content:
            # 降级：取 <body> 文本
            body = art_soup.find("body")
            content = body.get_text(separator="\n", strip=True) if body else ""

        if not content:
            logger.error(f"正文为空 source={source} article_url={article_link}")
            return None

        # 尝试从页面提取文章发布日期
        article_date: date | None = None
        for time_tag in art_soup.find_all(["time", "span", "div"]):
            text = time_tag.get_text(strip=True)
            # 匹配 2025-xx-xx 或 2026-xx-xx 格式
            import re
            m = re.search(r"(20\d{2})[-/](0?\d|1[0-2])[-/](0?\d|[12]\d|3[01])", text)
            if m:
                try:
                    article_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    break
                except ValueError:
                    continue

        return {"articleDate": article_date, "content": content, "articleUrl": article_link}

    except requests.RequestException as e:
        logger.error(f"HTTP请求失败 source={source} url={url} 错误={e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"解析失败 source={source} url={url} 错误={e}", exc_info=True)
        return None


def _saveRecord(db, brief_date: date, source: str, raw_content: str) -> bool:
    """插入 morning_brief 记录，已存在则跳过，返回是否插入成功"""
    record = MorningBrief(
        briefDate=brief_date,
        source=source,
        rawContent=raw_content,
    )
    try:
        db.add(record)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def runFetchMorningBrief() -> None:
    """定时任务：采集盘前纪要（每个交易日 09:00 北京时间执行）"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        for source, url in SOURCES.items():
            # 检查今天数据是否已存在
            existing = (
                db.query(MorningBrief)
                .filter(MorningBrief.briefDate == today, MorningBrief.source == source)
                .first()
            )
            if existing:
                logger.info(f"已存在今日记录，跳过 source={source} date={today}")
                continue

            result = _fetchLatestArticle(source, url)
            if not result:
                logger.error(f"采集失败 source={source}")
                continue

            inserted = _saveRecord(db, today, source, result["content"])
            if inserted:
                logger.info(f"盘前纪要保存成功 source={source} date={today}")
            else:
                logger.info(f"记录已存在（并发写入）跳过 source={source} date={today}")

    except Exception as e:
        logger.error(f"盘前纪要采集任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
