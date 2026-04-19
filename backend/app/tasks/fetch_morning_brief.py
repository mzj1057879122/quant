import re
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.morning_brief import MorningBrief
from app.tasks.summarize_morning_brief import runSummarizeMorningBrief
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
    # Cookie过期时内容会变空，后端日志会出现 ⚠️ Cookie已失效 错误，请更新
    "Cookie": "SESSION=NDI4YWJhM2UtNDM4Yi00YjU2LWJjNzgtNGFiNDdiYWMxYzhl; Hm_lvt_58aa18061df7855800f2a1b32d6da7f4=1774855487,1775547199,1775723406,1776070948; Hm_lpvt_58aa18061df7855800f2a1b32d6da7f4=1776330227",
}


def _decodeNuxtStr(s: str) -> str:
    """解码NUXT字符串：\\n/\\"/\\uXXXX"""
    s = s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s


def _extractFullText(article_url: str) -> str | None:
    """
    从文章详情页（/a/xxx）的NUXT数据中提取完整正文HTML，解析为纯文本。
    不需要Cookie，SSR直接返回。
    """
    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        nuxt_match = re.search(r'window\.__NUXT__\s*=\s*(.+?);\s*</script>', resp.text, re.DOTALL)
        if not nuxt_match:
            return None

        raw = nuxt_match.group(1)
        # 找最长的字符串（即文章HTML内容，通常>1000字符）
        long_strs = re.findall(r'"((?:[^"\\]|\\.){1000,})"', raw)
        if not long_strs:
            return None

        # 取最长的（排除脚本/样式等干扰）
        best = max(long_strs, key=len)
        html_content = _decodeNuxtStr(best)

        # 过滤：必须包含中文字符
        if not re.search(r'[\u4e00-\u9fff]', html_content):
            return None

        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        # 基本有效性检查
        if len(text) < 200 or "登录注册" in text:
            return None

        return text

    except Exception as e:
        logger.error(f"提取文章全文失败 url={article_url} 错误={e}", exc_info=True)
        return None


def _fetchArticlesByDate(source: str, url: str) -> list[dict]:
    """
    从用户主页获取文章列表（article_id + sync_time），
    返回 [{"articleDate": date, "articleId": str}, ...]
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 从HTML的a标签里找 /a/xxx 链接
        article_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.match(r'^/a/([a-z0-9]+)$', href)
            if m:
                article_links.append(m.group(1))

        if not article_links:
            # 降级：从NUXT数据提取
            nuxt_match = re.search(r'window\.__NUXT__\s*=\s*(.+?);\s*</script>', resp.text, re.DOTALL)
            if nuxt_match:
                raw = nuxt_match.group(1)
                article_links = re.findall(r'article_id:"([^"]+)"', raw)

        sync_times = []
        nuxt_match = re.search(r'window\.__NUXT__\s*=\s*(.+?);\s*</script>', resp.text, re.DOTALL)
        if nuxt_match:
            sync_times = re.findall(r'sync_time:"([^"]+)"', nuxt_match.group(1))

        articles = []
        for i, art_id in enumerate(article_links):
            try:
                st = sync_times[i] if i < len(sync_times) else None
                art_date = datetime.strptime(st[:10], "%Y-%m-%d").date() if st else None
                articles.append({"articleDate": art_date, "articleId": art_id})
            except Exception:
                continue

        return articles

    except Exception as e:
        logger.error(f"获取文章列表失败 source={source} 错误={e}", exc_info=True)
        return []


def _saveRecord(db, brief_date: date, source: str, raw_content: str) -> bool:
    existing = db.query(MorningBrief).filter(
        MorningBrief.briefDate == brief_date,
        MorningBrief.source == source
    ).first()
    if existing:
        # 如果之前是空壳/截断数据，更新
        if len(existing.rawContent or '') < 500:
            existing.rawContent = raw_content
            db.commit()
            return True
        return False
    try:
        db.add(MorningBrief(briefDate=brief_date, source=source, rawContent=raw_content))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def runFetchMorningBrief(targetDate: date | None = None) -> None:
    """
    采集盘前纪要。targetDate=None 时采今天；传入日期时补跑指定日期。
    """
    today = targetDate or date.today()
    if not targetDate and not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    db = SessionLocal()
    try:
        for source, url in SOURCES.items():
            articles = _fetchArticlesByDate(source, url)
            if not articles:
                logger.error(f"获取文章列表失败 source={source}")
                continue

            # 找目标日期的文章
            matched = next((a for a in articles if a["articleDate"] == today), None)
            if not matched:
                available = [a["articleDate"] for a in articles[:5]]
                logger.info(f"未找到目标日期文章 source={source} date={today} available={available}")
                continue

            # 抓完整全文
            art_url = f"https://www.jiuyangongshe.com/a/{matched['articleId']}"
            full_text = _extractFullText(art_url)

            if not full_text:
                logger.error(f"⚠️ Cookie已失效或文章内容为空 source={source} url={art_url}，请更新Cookie")
                continue

            saved = _saveRecord(db, today, source, full_text)
            if saved:
                logger.info(f"盘前纪要保存成功 source={source} date={today} len={len(full_text)}")
            else:
                logger.info(f"已存在有效记录，跳过 source={source} date={today}")

    except Exception as e:
        logger.error(f"盘前纪要采集任务异常 错误={e}", exc_info=True)
    finally:
        db.close()

    # 采集完成后生成 AI 摘要
    runSummarizeMorningBrief(today)
