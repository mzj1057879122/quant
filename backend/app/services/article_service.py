import asyncio
import html as htmlLib
import json
import os
import re
import time
from datetime import date, timedelta
from decimal import Decimal

import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.article import Article
from app.models.breakout_analysis import BreakoutAnalysis
from app.models.daily_quote import DailyQuote
from app.models.daily_summary import DailySummary
from app.models.previous_high import PreviousHigh
from app.models.stock import Stock
from app.utils.logger import setupLogger

logger = setupLogger("article_service")

CLAUDE_CLI = "/home/zejianma/.nvm/versions/node/v24.13.0/bin/claude"
WORK_DIR = "/home/zejianma/quant"
ARTICLE_TIMEOUT = 60
SUMMARY_TIMEOUT = 120


# ==================== 股票技术数据采集 ====================

def matchStockNames(db: Session, names: list[str]) -> dict[str, str]:
    """股票名→代码映射，查stock表精确+模糊匹配"""
    result = {}
    if not names:
        return result

    allStocks = db.query(Stock.stockName, Stock.stockCode).filter(Stock.isActive == 1).all()
    nameMap = {s.stockName: s.stockCode for s in allStocks}

    for name in names:
        name = name.strip()
        if not name:
            continue
        # 精确匹配
        if name in nameMap:
            result[name] = nameMap[name]
            continue
        # contains匹配（名字包含在stock_name里，或stock_name包含在名字里）
        for sName, sCode in nameMap.items():
            if name in sName or sName in name:
                result[name] = sCode
                break

    return result


def getStockTechnicalData(db: Session, stockCode: str) -> dict | None:
    """获取单只股票的技术分析数据"""
    stock = db.query(Stock).filter(Stock.stockCode == stockCode).first()
    if not stock:
        return None

    # 最近10天行情
    recentQuotes = (
        db.query(DailyQuote)
        .filter(DailyQuote.stockCode == stockCode)
        .order_by(DailyQuote.tradeDate.desc())
        .limit(10)
        .all()
    )
    if not recentQuotes:
        return None

    latest = recentQuotes[0]
    latestClose = float(latest.closePrice)

    # 5日涨幅、10日涨幅
    changePct5d = None
    changePct10d = None
    if len(recentQuotes) >= 5 and recentQuotes[4].closePrice > 0:
        changePct5d = round((latestClose / float(recentQuotes[4].closePrice) - 1) * 100, 2)
    if len(recentQuotes) >= 10 and recentQuotes[9].closePrice > 0:
        changePct10d = round((latestClose / float(recentQuotes[9].closePrice) - 1) * 100, 2)

    # 5日量比（今日成交量 / 前5日平均成交量）
    volumeRatio5d = None
    if len(recentQuotes) >= 6:
        prevAvgVol = sum(q.volume for q in recentQuotes[1:6]) / 5
        if prevAvgVol > 0:
            volumeRatio5d = round(latest.volume / prevAvgVol, 2)

    # 前高位置
    activeHigh = (
        db.query(PreviousHigh)
        .filter(PreviousHigh.stockCode == stockCode, PreviousHigh.status == "active")
        .first()
    )
    previousHigh = None
    distToHigh = None
    currentStatus = "below"
    if activeHigh:
        previousHigh = float(activeHigh.highPrice)
        if previousHigh > 0:
            distToHigh = round((latestClose / previousHigh - 1) * 100, 2)
        approachPct = 0.95
        if latestClose >= previousHigh:
            currentStatus = "breakout"
        elif latestClose >= previousHigh * approachPct:
            currentStatus = "approaching"

    # 历史突破成功率
    analysis = db.query(BreakoutAnalysis).filter(BreakoutAnalysis.stockCode == stockCode).first()
    breakoutSuccessRate = float(analysis.successRate) if analysis and analysis.successRate else None

    # 最近5天行情摘要
    recent5 = []
    for q in recentQuotes[:5]:
        recent5.append({
            "date": q.tradeDate.isoformat(),
            "close": float(q.closePrice),
            "changePct": float(q.changePct) if q.changePct is not None else None,
            "volume": q.volume,
        })
    recent5.reverse()

    return {
        "code": stockCode,
        "name": stock.stockName,
        "latestClose": latestClose,
        "changePct5d": changePct5d,
        "changePct10d": changePct10d,
        "volumeRatio5d": volumeRatio5d,
        "previousHigh": previousHigh,
        "distToHigh": distToHigh,
        "breakoutSuccessRate": breakoutSuccessRate,
        "currentStatus": currentStatus,
        "recentQuotes": recent5,
    }


def collectStockPool(db: Session, articles: list, watchList: list[str] | None = None) -> list[dict]:
    """收集股票池并获取技术数据：文章提到的热门票 ∪ 关注列表"""
    # 从文章分析结果中提取股票名
    stockNames = set()
    for a in articles:
        if not a.resultSummary:
            continue
        try:
            parsed = json.loads(a.resultSummary)
        except json.JSONDecodeError:
            continue
        for sv in parsed.get("stockViews", []):
            name = sv.get("name", "").strip()
            if name:
                stockNames.add(name)

    # 股票名→代码匹配
    nameToCode = matchStockNames(db, list(stockNames))

    # 合并关注列表的代码
    allCodes = set(nameToCode.values())
    if watchList:
        allCodes.update(watchList)

    # 获取每只票的技术数据
    technicalData = []
    for code in allCodes:
        data = getStockTechnicalData(db, code)
        if data:
            technicalData.append(data)

    logger.info(f"股票池收集完成 文章提及={len(stockNames)} 匹配={len(nameToCode)} 关注列表={len(watchList or [])} 技术数据={len(technicalData)}")
    return technicalData


# ==================== Prompt 构建 ====================

def buildArticlePrompt(article: Article) -> str:
    """单篇分析 prompt：提取作者观点，轻量快速"""
    header = f"文章日期：{article.articleDate}"
    if article.title:
        header += f"\n标题：{article.title}"
    if article.author:
        header += f"\n作者：{article.author}"
    if article.source:
        header += f"\n来源：{article.source}"

    return f"""你是A股短线交易分析助手。请分析以下文章，提取作者的观点和策略。

{header}

文章内容：
{article.content}

请严格输出以下JSON格式（不要用markdown代码块包裹，直接输出JSON）：
{{
  "marketView": "作者对大盘/市场情绪的整体判断（一两句话）",
  "stockViews": [
    {{
      "name": "股票名称",
      "opinion": "看多/看空/中性/观望",
      "logic": "作者的分析逻辑",
      "strategy": "作者建议的操作策略",
      "risk": "作者提到的风险点"
    }}
  ],
  "sectorViews": [
    {{
      "name": "板块名称",
      "opinion": "看多/看空/中性",
      "logic": "板块逻辑",
      "keyStocks": ["板块中提到的关键票"]
    }}
  ],
  "keyPredictions": ["作者对未来几天的关键预判"],
  "tradingAdvice": "作者给出的具体操作建议总结"
}}

注意：
- stockViews 只提取作者有明确观点的个股，不要凑数
- opinion 必须是"看多/看空/中性/观望"四选一
- 保持客观提取，不要添加你自己的判断"""


def buildDailySummaryPrompt(articles: list[dict], prevSummaries: list[dict], framework: dict | None = None) -> str:
    """每日汇总 prompt：横向对比 + 纵向关联（纯策略面）+ 框架指导"""
    # 当日各作者分析
    articlesSection = ""
    for i, a in enumerate(articles, 1):
        articlesSection += f"\n--- 作者{i}: {a['author']} ({a['title']}) ---\n{a['analysis']}\n"

    # 前两天汇总
    prevSection = ""
    if prevSummaries:
        for ps in prevSummaries:
            prevSection += f"\n--- {ps['date']} 综合策略 ---\n"
            prevSection += f"共识: {ps.get('consensus', '无')}\n"
            prevSection += f"分歧: {ps.get('divergence', '无')}\n"
            prevSection += f"策略: {ps.get('strategy', '无')}\n"
    else:
        prevSection = "（暂无前两天的汇总数据）"

    # 交易框架（如有）
    frameworkSection = ""
    if framework:
        frameworkSection = f"""

== 你的交易方法论框架 ==
{json.dumps(framework, ensure_ascii=False)}

请基于此框架来评判各作者观点：哪些观点符合框架中的进场/出场规则，哪些违背风控原则，并在 strategy 中明确引用框架规则。"""

    return f"""你是A股短线交易策略分析师。请综合分析以下多位作者的观点，生成今日综合策略。

== 今日各作者分析 ==
{articlesSection}

== 前两天综合策略 ==
{prevSection}
{frameworkSection}

请从以下维度综合分析，直接输出JSON（不要用markdown代码块包裹）：
{{
  "consensus": "多位作者的共识要点（他们都认同什么）",
  "divergence": "作者间的分歧点（谁看多谁看空，分歧在哪）",
  "stockViews": [
    {{
      "name": "股票名称",
      "bullCount": 0,
      "bearCount": 0,
      "neutralCount": 0,
      "synthesis": "综合多位作者的看法",
      "suggestedAction": "综合建议操作"
    }}
  ],
  "sectorViews": [
    {{
      "name": "板块名称",
      "outlook": "综合展望",
      "keyPoints": "关键要点"
    }}
  ],
  "strategy": "明日综合应对策略（具体到怎么操作）",
  "evolution": "与前两天策略对比：哪些预判被验证了、哪些失效了、市场情绪怎么演变的"
}}

注意：
- 重点突出作者间的共识和分歧，不要简单罗列
- strategy 要具体可执行，不要空话
- evolution 要明确对比，不要泛泛而谈"""


def _formatTechSection(technicalData: list[dict]) -> str:
    """格式化技术数据为文本段落"""
    section = ""
    for td in technicalData:
        section += f"\n{td['name']}({td['code']}):\n"
        section += f"  最新收盘: {td['latestClose']}"
        if td.get('changePct5d') is not None:
            section += f" | 5日涨幅: {td['changePct5d']:+.1f}%"
        if td.get('changePct10d') is not None:
            section += f" | 10日涨幅: {td['changePct10d']:+.1f}%"
        section += "\n"
        if td.get('volumeRatio5d') is not None:
            section += f"  5日量比: {td['volumeRatio5d']}"
        if td.get('previousHigh') is not None:
            section += f" | 前高: {td['previousHigh']}"
        if td.get('distToHigh') is not None:
            section += f" | 离前高: {td['distToHigh']:+.1f}%"
        section += "\n"
        if td.get('breakoutSuccessRate') is not None:
            section += f"  历史突破成功率: {td['breakoutSuccessRate']:.0f}%"
        statusMap = {"approaching": "接近前高", "breakout": "已突破", "below": "在前高下方"}
        section += f" | 当前状态: {statusMap.get(td.get('currentStatus', ''), td.get('currentStatus', ''))}\n"
        if td.get('recentQuotes'):
            closes = "→".join(f"{q['close']}" for q in td['recentQuotes'])
            section += f"  最近5天收盘: {closes}\n"
    return section


def buildProbabilityPrompt(stockViews: list[dict], technicalData: list[dict]) -> str:
    """第二步 prompt：结合策略观点+技术数据，输出次日上涨概率"""
    # 策略观点摘要
    viewsSection = ""
    for sv in stockViews:
        viewsSection += f"\n{sv.get('name', '?')}: 看多{sv.get('bullCount', 0)} 看空{sv.get('bearCount', 0)} 中性{sv.get('neutralCount', 0)}"
        viewsSection += f" | 综合: {sv.get('synthesis', '')}"
        viewsSection += f" | 建议: {sv.get('suggestedAction', '')}\n"

    techSection = _formatTechSection(technicalData)

    return f"""你是A股短线量化分析师。请结合以下情绪面观点和技术面数据，给每只股票评估次日上涨概率。

== 多作者综合观点 ==
{viewsSection}

== 个股技术数据 ==
{techSection}

请直接输出JSON数组（不要用markdown代码块包裹）：
[
  {{
    "name": "股票名称",
    "probability": 50,
    "reason": "一句话说明概率依据"
  }}
]

评估规则：
- probability 为0-100整数，代表次日上涨概率
- 综合考虑：作者观点方向（看多人数多→加分）、技术趋势（5日/10日涨幅为正→加分）、量能（量比>1→加分）、前高位置（接近前高且历史突破率高→加分，突破失败风险→减分）
- 只输出有技术数据的股票，没有行情数据的跳过
- reason 要简洁，点出最关键的1-2个因素"""


# ==================== Claude CLI 调用 ====================

async def callClaude(prompt: str, timeout: int) -> tuple[str, str, int]:
    """调用 Claude CLI，返回 (stdout, stderr, returncode)"""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    nodeBin = os.path.dirname(CLAUDE_CLI)
    if nodeBin not in env.get("PATH", ""):
        env["PATH"] = nodeBin + ":" + env.get("PATH", "")
    process = await asyncio.create_subprocess_exec(
        CLAUDE_CLI,
        "-p", prompt,
        "--model", "sonnet",
        "--max-turns", "1",
        cwd=WORK_DIR,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(
        process.communicate(), timeout=timeout
    )
    return (
        stdout.decode("utf-8", errors="replace").strip(),
        stderr.decode("utf-8", errors="replace").strip(),
        process.returncode,
    )


def parseJson(output: str) -> dict | None:
    """从 Claude 输出中解析 JSON"""
    # 直接解析
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        pass
    # markdown 代码块
    m = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", output, re.S)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # { 到 } 之间
    start = output.find("{")
    end = output.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(output[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ==================== 文章提交与单篇分析 ====================

def submitArticle(db: Session, title: str | None, author: str | None, content: str, source: str | None, articleDate=None, sourceUrl: str | None = None) -> Article:
    """提交文章，创建DB记录"""
    article = Article(
        title=title,
        author=author,
        content=content,
        source=source,
        sourceUrl=sourceUrl,
        articleDate=articleDate or date.today(),
        status="pending",
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    logger.info(f"文章已提交 id={article.id}")
    return article


async def processArticleAsync(articleId: int) -> None:
    """异步单篇分析：提取作者观点"""
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == articleId).first()
        if not article:
            logger.error(f"文章不存在 id={articleId}")
            return

        article.status = "processing"
        db.commit()

        startTime = time.time()
        try:
            prompt = buildArticlePrompt(article)
            stdout, stderr, returncode = await callClaude(prompt, ARTICLE_TIMEOUT)
            duration = int(time.time() - startTime)

            if returncode != 0 or not stdout:
                article.status = "failed"
                article.errorMessage = stderr or f"CLI退出码: {returncode}"
                article.processDuration = duration
                logger.error(f"单篇分析失败 id={articleId} returncode={returncode}")
                db.commit()
                return

            parsed = parseJson(stdout)
            if not parsed:
                article.status = "failed"
                article.errorMessage = f"JSON解析失败，原始输出前500字：{stdout[:500]}"
                article.processDuration = duration
                logger.error(f"JSON解析失败 id={articleId}")
                db.commit()
                return

            article.status = "completed"
            article.resultSummary = json.dumps(parsed, ensure_ascii=False)
            article.processDuration = duration
            logger.info(f"单篇分析完成 id={articleId} duration={duration}s")

        except asyncio.TimeoutError:
            duration = int(time.time() - startTime)
            article.status = "failed"
            article.errorMessage = f"处理超时（{ARTICLE_TIMEOUT}秒）"
            article.processDuration = duration
            logger.error(f"单篇分析超时 id={articleId}")

        except Exception as e:
            duration = int(time.time() - startTime)
            article.status = "failed"
            article.errorMessage = str(e)
            article.processDuration = duration
            logger.error(f"单篇分析异常 id={articleId}", exc_info=True)

        db.commit()

    except Exception as e:
        logger.error(f"processArticleAsync异常 id={articleId}", exc_info=True)
    finally:
        db.close()


# ==================== 每日汇总 ====================

async def generateDailySummaryAsync(summaryDate: date) -> None:
    """异步生成每日综合策略（两步：策略汇总 → 概率分析）"""
    db = SessionLocal()
    try:
        # 获取或创建当日汇总记录
        summary = db.query(DailySummary).filter(DailySummary.summaryDate == summaryDate).first()
        if not summary:
            summary = DailySummary(summaryDate=summaryDate, status="pending")
            db.add(summary)
            db.commit()
            db.refresh(summary)

        summary.status = "processing"
        db.commit()

        startTime = time.time()
        try:
            # 1. 读取当日所有已完成文章的分析结果
            articles = db.query(Article).filter(
                Article.articleDate == summaryDate,
                Article.status == "completed",
            ).all()

            if not articles:
                summary.status = "failed"
                summary.errorMessage = "当日没有已完成分析的文章"
                db.commit()
                return

            articleData = []
            for a in articles:
                articleData.append({
                    "author": a.author or "未知",
                    "title": a.title or "无标题",
                    "analysis": a.resultSummary or "{}",
                })

            # 2. 读取前2天的每日汇总
            prevSummaries = []
            for dayOffset in [1, 2]:
                prevDate = summaryDate - timedelta(days=dayOffset)
                prev = db.query(DailySummary).filter(
                    DailySummary.summaryDate == prevDate,
                    DailySummary.status == "completed",
                ).first()
                if prev:
                    prevSummaries.append({
                        "date": str(prev.summaryDate),
                        "consensus": prev.consensus,
                        "divergence": prev.divergence,
                        "strategy": prev.strategy,
                    })

            # 获取交易框架（如有）
            from app.services.knowledge_service import getLatestFramework
            framework = getLatestFramework(db)

            # ===== 第一步：策略汇总 =====
            prompt1 = buildDailySummaryPrompt(articleData, prevSummaries, framework)
            stdout1, stderr1, rc1 = await callClaude(prompt1, SUMMARY_TIMEOUT)
            step1Duration = int(time.time() - startTime)

            if rc1 != 0 or not stdout1:
                summary.status = "failed"
                summary.errorMessage = stderr1 or f"策略汇总CLI退出码: {rc1}"
                summary.processDuration = step1Duration
                db.commit()
                return

            parsed1 = parseJson(stdout1)
            if not parsed1:
                summary.status = "failed"
                summary.errorMessage = f"策略汇总JSON解析失败，原始输出前500字：{stdout1[:500]}"
                summary.processDuration = step1Duration
                db.commit()
                return

            # 先存策略结果到DB
            stockViews = parsed1.get("stockViews", [])
            summary.articleCount = len(articles)
            summary.consensus = parsed1.get("consensus", "")
            summary.divergence = parsed1.get("divergence", "")
            summary.stockViews = json.dumps(stockViews, ensure_ascii=False)
            summary.sectorViews = json.dumps(parsed1.get("sectorViews", []), ensure_ascii=False)
            summary.strategy = parsed1.get("strategy", "")
            summary.evolution = parsed1.get("evolution", "")
            summary.rawOutput = stdout1
            db.commit()
            logger.info(f"策略汇总完成 date={summaryDate} duration={step1Duration}s")

            # ===== 第二步：概率分析 =====
            from app.services.config_service import getWatchList
            watchList = getWatchList(db)
            technicalData = collectStockPool(db, articles, watchList)

            if technicalData:
                prompt2 = buildProbabilityPrompt(stockViews, technicalData)
                stdout2, stderr2, rc2 = await callClaude(prompt2, SUMMARY_TIMEOUT)
                totalDuration = int(time.time() - startTime)

                if rc2 == 0 and stdout2:
                    parsed2 = parseJson(stdout2)
                    if parsed2:
                        # parsed2 是 list，把 probability 合并回 stockViews
                        probMap = {}
                        probList = parsed2 if isinstance(parsed2, list) else parsed2.get("stocks", parsed2.get("data", []))
                        for item in probList:
                            name = item.get("name", "")
                            if name:
                                probMap[name] = {
                                    "probability": item.get("probability"),
                                    "reason": item.get("reason", ""),
                                }
                        for sv in stockViews:
                            prob = probMap.get(sv.get("name", ""))
                            if prob:
                                sv["probability"] = prob["probability"]
                                sv["reason"] = prob["reason"]
                        # 补充只在技术数据中、不在 stockViews 中的票
                        existNames = {sv.get("name") for sv in stockViews}
                        for item in probList:
                            if item.get("name") and item["name"] not in existNames:
                                stockViews.append({
                                    "name": item["name"],
                                    "probability": item.get("probability"),
                                    "reason": item.get("reason", ""),
                                    "synthesis": "仅技术面分析（无作者观点）",
                                    "suggestedAction": "",
                                })
                        summary.stockViews = json.dumps(stockViews, ensure_ascii=False)
                        summary.rawOutput = stdout1 + "\n\n===== 概率分析 =====\n" + stdout2
                        db.commit()
                        logger.info(f"概率分析完成 date={summaryDate} 匹配={len(probMap)}只")
                    else:
                        logger.error(f"概率分析JSON解析失败 date={summaryDate}")
                else:
                    logger.error(f"概率分析CLI失败 date={summaryDate} rc={rc2}")

                summary.processDuration = totalDuration
            else:
                summary.processDuration = step1Duration
                logger.info(f"无技术数据，跳过概率分析 date={summaryDate}")

            summary.status = "completed"
            logger.info(f"每日汇总完成 date={summaryDate} articles={len(articles)} duration={int(time.time() - startTime)}s")

        except asyncio.TimeoutError:
            duration = int(time.time() - startTime)
            summary.status = "failed"
            summary.errorMessage = f"处理超时（{SUMMARY_TIMEOUT}秒）"
            summary.processDuration = duration
            logger.error(f"每日汇总超时 date={summaryDate}")

        except Exception as e:
            duration = int(time.time() - startTime)
            summary.status = "failed"
            summary.errorMessage = str(e)
            summary.processDuration = duration
            logger.error(f"每日汇总异常 date={summaryDate}", exc_info=True)

        db.commit()

    except Exception as e:
        logger.error(f"generateDailySummaryAsync异常 date={summaryDate}", exc_info=True)
    finally:
        db.close()


# ==================== 查询 ====================

def getArticleById(db: Session, articleId: int) -> Article | None:
    return db.query(Article).filter(Article.id == articleId).first()


def getArticleList(db: Session, status: str | None = None, articleDate: date | None = None, page: int = 1, pageSize: int = 20) -> tuple[list[Article], int]:
    query = db.query(Article)
    if status:
        query = query.filter(Article.status == status)
    if articleDate:
        query = query.filter(Article.articleDate == articleDate)
    total = query.count()
    items = query.order_by(Article.createdAt.desc()).offset((page - 1) * pageSize).limit(pageSize).all()
    return items, total


def batchUpdateArticleDate(db: Session, articleIds: list[int], newDate: date) -> int:
    """批量更新文章日期"""
    count = (
        db.query(Article)
        .filter(Article.id.in_(articleIds))
        .update({"article_date": newDate}, synchronize_session=False)
    )
    db.commit()
    logger.info(f"批量更新日期 ids={articleIds} date={newDate} count={count}")
    return count


def getDailySummary(db: Session, summaryDate: date) -> DailySummary | None:
    return db.query(DailySummary).filter(DailySummary.summaryDate == summaryDate).first()


def getDailySummaryList(db: Session, page: int = 1, pageSize: int = 10) -> tuple[list[DailySummary], int]:
    query = db.query(DailySummary)
    total = query.count()
    items = query.order_by(DailySummary.summaryDate.desc()).offset((page - 1) * pageSize).limit(pageSize).all()
    return items, total


# ==================== 启动恢复 ====================

def recoverStuckArticles(db: Session) -> int:
    """启动时恢复卡住的文章和汇总"""
    count = 0
    for model in [Article, DailySummary]:
        stuck = db.query(model).filter(model.status.in_(["processing", "pending"])).all()
        for item in stuck:
            item.status = "failed"
            item.errorMessage = "服务重启导致处理中断，请重试"
            count += 1
    if count:
        db.commit()
        logger.info(f"恢复卡住的记录 count={count}")
    return count


# ==================== 淘股吧提取 ====================

def extractFromTgb(url: str) -> dict:
    """从淘股吧URL提取文章内容"""
    resp = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.tgb.cn/",
        },
        timeout=15,
    )
    resp.raise_for_status()
    page = resp.text

    # 作者
    m = re.search(r'id="gioMsg"[^>]*userName="([^"]+)"', page)
    author = m.group(1) if m else None

    # 标题
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    rawTitle = m.group(1).strip() if m else ""
    title = re.sub(r"_[^_]*_\s*淘股吧\s*$", "", rawTitle).strip()

    # 日期
    articleDate = date.today()
    m = re.search(r"(\d{2})\.(\d{2})", title)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            articleDate = date(date.today().year, month, day)
        except ValueError:
            pass

    # 正文：固定容器 div.article-text.p_coten#first
    content = ""
    m = re.search(r'<div[^>]*class="article-text p_coten"[^>]*>(.*?)<!-- 设置播放器', page, re.S)
    if not m:
        m = re.search(r'<div[^>]*id="first"[^>]*>(.*?)<!-- 设置播放器', page, re.S)
    if m:
        chunk = m.group(1)
        chunk = re.sub(r"<br\s*/?\s*>", "\n", chunk)
        chunk = re.sub(r"<a[^>]*>([^<]*)</a>", r"\1", chunk)
        chunk = re.sub(r"<[^>]+>", "", chunk)
        content = htmlLib.unescape(chunk).strip()

    if not content or len(content) < 20:
        raise ValueError("提取正文失败，页面结构可能已变化")

    return {
        "title": title,
        "author": author,
        "content": content,
        "source": "淘股吧",
        "sourceUrl": url,
        "articleDate": articleDate,
    }


def extractFromJiuyan(url: str) -> dict:
    """从韭研公社URL提取文章内容（Nuxt SSR页面，正文在 window.__NUXT__ 中）"""
    resp = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        },
        timeout=15,
    )
    resp.raise_for_status()
    page = resp.text

    # 标题：从 <title> 提取，去掉 -韭研公社 后缀
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    rawTitle = m.group(1).strip() if m else ""
    title = re.sub(r"-韭研公社\s*$", "", rawTitle).strip()

    # 作者：username-box 下的 fs16-bold
    m = re.search(r'username-box.*?class="fs16-bold"[^>]*>(.*?)<', page, re.S)
    author = m.group(1).strip() if m else None

    # 日期：class="date ..." 或 class="...date..."
    articleDate = date.today()
    m = re.search(r'class="[^"]*date[^"]*"[^>]*>(\d{4}-\d{2}-\d{2})', page)
    if m:
        try:
            articleDate = date.fromisoformat(m.group(1))
        except ValueError:
            pass

    # 正文：从 window.__NUXT__ 的 content 字段提取
    content = ""
    nuxtIdx = page.find("window.__NUXT__")
    if nuxtIdx > 0:
        nuxt = page[nuxtIdx:]
        ci = nuxt.find('content:"')
        if ci > 0:
            start = ci + 9
            pos = start
            while pos < len(nuxt):
                ch = nuxt[pos]
                if ch == '\\':
                    pos += 2
                    continue
                if ch == '"':
                    break
                pos += 1
            raw = nuxt[start:pos]
            # 解码 \uXXXX 转义
            raw = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), raw)
            raw = raw.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            # 去 HTML
            raw = re.sub(r"<br\s*/?\s*>", "\n", raw)
            raw = re.sub(r"<p[^>]*>", "\n", raw)
            raw = re.sub(r"<[^>]+>", "", raw)
            content = htmlLib.unescape(raw).strip()
            content = re.sub(r"\n{3,}", "\n\n", content)

    if not content or len(content) < 20:
        raise ValueError("提取正文失败，页面结构可能已变化")

    return {
        "title": title,
        "author": author,
        "content": content,
        "source": "韭研公社",
        "sourceUrl": url,
        "articleDate": articleDate,
    }


def extractFromUrl(url: str) -> dict:
    """根据URL自动识别来源并提取文章"""
    if "tgb.cn" in url:
        return extractFromTgb(url)
    if "jiuyangongshe.com" in url:
        return extractFromJiuyan(url)
    raise ValueError(f"暂不支持该网站的自动提取: {url}")
