import asyncio
import json
import time

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.trading_knowledge import TradingKnowledge
from app.models.trading_framework import TradingFramework
from app.services.article_service import callClaude, parseJson, extractFromUrl
from app.utils.logger import setupLogger

logger = setupLogger("knowledge_service")

EXTRACT_TIMEOUT = 60
FRAMEWORK_TIMEOUT = 120


# ==================== Prompt 构建 ====================

def buildExtractPrompt(knowledge: TradingKnowledge) -> str:
    """单篇心得提取交易原则 prompt（v2: 7模块结构）"""
    header = f"标题：{knowledge.title}"
    if knowledge.author:
        header += f"\n作者：{knowledge.author}"
    if knowledge.category:
        header += f"\n分类：{knowledge.category}"

    return f"""你是交易方法论分析师。请从以下交易心得中提取核心交易原则，按7个模块归类。

{header}

文章内容：
{knowledge.content}

请严格输出以下JSON格式（不要用markdown代码块包裹，直接输出JSON）。只填有内容的模块，没提到的模块输出空对象 {{}}：
{{
  "tradingStyle": "短线/波段/趋势/综合",
  "corePrinciples": ["核心原则（不超过5条）"],
  "modules": {{
    "marketAssessment": {{
      "rules": [
        {{"dimension": "判断维度(如指数/情绪/量能)", "levels": {{
          "强势": {{"criteria": ["条件"], "action": "操作"}},
          "震荡": {{"criteria": [], "action": ""}},
          "弱势": {{"criteria": [], "action": ""}}
        }}}}
      ]
    }},
    "sectorScreening": {{
      "screeningRules": ["板块筛选条件"],
      "grading": [{{"level": "A级/B级/C级", "criteria": "标准", "action": "操作"}}],
      "rotationRules": ["轮动规则"]
    }},
    "capitalFlow": {{
      "phases": [
        {{"phase": "建仓/拉升/出货", "signals": ["信号"], "action": "操作"}}
      ]
    }},
    "patterns": {{
      "buyPatterns": [{{"name": "形态名", "trigger": "触发条件", "entry": "入场点", "stopLoss": "止损点"}}],
      "sellSignals": ["卖出条件"]
    }},
    "tactics": {{
      "strategies": [
        {{"name": "战法名", "marketCondition": "适用市况", "conditions": ["条件"], "entry": "入场", "stopProfit": "止盈", "stopLoss": "止损"}}
      ]
    }},
    "intradayTiming": {{
      "buySignals": ["分时买入信号"],
      "sellSignals": ["分时卖出信号"]
    }},
    "riskManagement": {{
      "positionRules": [{{"scenario": "场景", "singlePosition": "单只仓位", "totalPosition": "整体仓位"}}],
      "stopLossRules": ["止损规则"],
      "stopProfitRules": ["止盈规则"],
      "discipline": ["交易纪律"]
    }}
  }},
  "keyQuotes": ["原文金句（不超过5条）"]
}}

注意：
- 只提取作者明确表达的原则，不要自行推断
- 大部分心得只涉及1-3个模块，其余模块输出空对象 {{}}
- tactics.strategies 的 name 要具体（如"首板打板"、"龙头回封"），不要笼统
- patterns.buyPatterns 的 trigger 要有量化条件（如"缩量到前一日50%以下"）
- corePrinciples 是最核心的交易哲学，不超过5条"""


def _summarizePrinciplesV2(principles: dict, author: str, title: str) -> str:
    """v2格式：按模块摘要"""
    lines = [f"风格: {principles.get('tradingStyle', '未知')}"]
    if principles.get("corePrinciples"):
        lines.append(f"核心: {'; '.join(principles['corePrinciples'])}")
    modules = principles.get("modules", {})
    moduleNames = {
        "marketAssessment": "大盘判断", "sectorScreening": "板块筛选",
        "capitalFlow": "资金行为", "patterns": "K线形态",
        "tactics": "战法", "intradayTiming": "分时技法", "riskManagement": "风控",
    }
    for key, label in moduleNames.items():
        mod = modules.get(key, {})
        if not mod:
            continue
        # 紧凑摘要：取每个模块的核心内容
        parts = []
        if key == "marketAssessment":
            for r in mod.get("rules", []):
                parts.append(r.get("dimension", ""))
        elif key == "sectorScreening":
            parts = mod.get("screeningRules", [])[:3]
        elif key == "capitalFlow":
            for p in mod.get("phases", []):
                parts.append(f"{p.get('phase', '')}:{','.join(p.get('signals', []))}")
        elif key == "patterns":
            for bp in mod.get("buyPatterns", []):
                parts.append(f"{bp.get('name', '')}({bp.get('trigger', '')})")
            parts.extend(mod.get("sellSignals", [])[:2])
        elif key == "tactics":
            for s in mod.get("strategies", []):
                parts.append(f"{s.get('name', '')}[{s.get('marketCondition', '')}]")
        elif key == "intradayTiming":
            parts = (mod.get("buySignals", []) + mod.get("sellSignals", []))[:3]
        elif key == "riskManagement":
            parts = mod.get("stopLossRules", [])[:2] + mod.get("discipline", [])[:2]
        if parts:
            lines.append(f"{label}: {'; '.join(str(p) for p in parts)}")
    if principles.get("keyQuotes"):
        lines.append(f"金句: {'; '.join(principles['keyQuotes'][:2])}")
    return "\n".join(lines)


def _summarizePrinciplesV1(principles: dict) -> str:
    """v1旧格式兼容摘要"""
    lines = [f"风格: {principles.get('tradingStyle', '未知')}"]
    if principles.get("corePrinciples"):
        lines.append(f"核心: {'; '.join(principles['corePrinciples'])}")
    if principles.get("entryRules"):
        entries = [f"{r['pattern']}({r['condition']})" for r in principles["entryRules"]]
        lines.append(f"进场/战法: {'; '.join(entries)}")
    if principles.get("exitRules"):
        exits = [f"{r['pattern']}({r['condition']})" for r in principles["exitRules"]]
        lines.append(f"出场/形态: {'; '.join(exits)}")
    if principles.get("riskManagement"):
        lines.append(f"风控: {'; '.join(principles['riskManagement'])}")
    if principles.get("emotionRules"):
        lines.append(f"纪律: {'; '.join(principles['emotionRules'])}")
    return "\n".join(lines)


def buildFrameworkPrompt(principlesList: list[dict], currentFramework: dict | None) -> str:
    """合成交易框架 prompt（v2: 7模块结构）"""
    # 每篇原则摘要，按模块聚合，保持紧凑
    principlesSection = ""
    for i, p in enumerate(principlesList, 1):
        principlesSection += f"\n--- 来源{i}: {p['author']} ({p['title']}) ---\n"
        principles = p["principles"]
        # 兼容新旧格式
        if principles.get("modules"):
            principlesSection += _summarizePrinciplesV2(principles, p["author"], p["title"]) + "\n"
        else:
            principlesSection += _summarizePrinciplesV1(principles) + "\n"

    currentSection = ""
    if currentFramework:
        currentSection = f"\n== 当前框架（在此基础上更新） ==\n{json.dumps(currentFramework, ensure_ascii=False, indent=2)}\n"

    return f"""你是交易系统设计师。请将以下多位交易者的原则合成为一套系统性交易框架，按7个决策模块组织。

== 各位交易者的提取原则 ==
{principlesSection}
{currentSection}
请综合所有来源，输出统一的7模块交易框架JSON（不要用markdown代码块包裹，直接输出JSON）：
{{
  "tradingPhilosophy": "核心交易哲学（一段话总结）",
  "decisionChain": ["marketAssessment", "sectorScreening", "capitalFlow", "patterns", "tactics", "intradayTiming", "riskManagement"],
  "modules": {{
    "marketAssessment": {{
      "name": "大盘大势判断",
      "purpose": "判断是否开仓及仓位上限",
      "rules": [
        {{"dimension": "判断维度", "levels": {{
          "强势": {{"criteria": ["条件"], "action": "操作"}},
          "震荡": {{"criteria": [], "action": ""}},
          "弱势": {{"criteria": [], "action": ""}}
        }}}}
      ]
    }},
    "sectorScreening": {{
      "name": "板块轮动与主线判断",
      "purpose": "筛选核心赛道",
      "screeningRules": ["筛选条件"],
      "grading": [{{"level": "A级/B级/C级", "criteria": "标准", "action": "操作"}}],
      "rotationRules": ["轮动规则"]
    }},
    "capitalFlow": {{
      "name": "主力资金行为分析",
      "purpose": "识别资金动向",
      "phases": [{{"phase": "阶段", "signals": ["信号"], "action": "操作"}}]
    }},
    "patterns": {{
      "name": "K线与形态交易法",
      "purpose": "识别高概率形态",
      "buyPatterns": [{{"name": "形态名", "trigger": "触发条件", "entry": "入场点", "stopLoss": "止损点"}}],
      "sellSignals": ["卖出条件"]
    }},
    "tactics": {{
      "name": "涨停战法",
      "purpose": "A股短线核心玩法",
      "strategies": [{{"name": "战法名", "marketCondition": "适用市况", "conditions": ["条件"], "entry": "入场", "stopProfit": "止盈", "stopLoss": "止损", "source": "来自谁"}}]
    }},
    "intradayTiming": {{
      "name": "分时交易技法",
      "purpose": "日内择时",
      "buySignals": ["买入信号"],
      "sellSignals": ["卖出信号"]
    }},
    "riskManagement": {{
      "name": "风控与资金管理",
      "purpose": "杜绝大亏保住利润",
      "positionRules": [{{"scenario": "场景", "singlePosition": "单只仓位", "totalPosition": "整体仓位"}}],
      "stopLossRules": ["止损规则"],
      "stopProfitRules": ["止盈规则"],
      "discipline": ["交易纪律"]
    }}
  }}
}}

注意：
- 如果有当前框架，在其基础上整合新来源的原则，去重合并
- 不同来源有冲突时，都保留并标注来源（在 source 字段），让用户自行取舍
- 每个模块的规则要具体可执行，有量化阈值更佳，不要空话
- 没有内容的模块保留结构但内容为空数组"""


# ==================== 提交与处理 ====================

def submitKnowledge(db: Session, title: str, author: str | None, content: str,
                    source: str | None, category: str | None, sourceUrl: str | None = None) -> TradingKnowledge:
    """提交交易心得"""
    knowledge = TradingKnowledge(
        title=title,
        author=author,
        content=content,
        source=source,
        sourceUrl=sourceUrl,
        category=category,
        status="pending",
    )
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)
    logger.info(f"交易心得已提交 id={knowledge.id}")
    return knowledge


async def processKnowledgeAsync(knowledgeId: int) -> None:
    """异步提取交易原则"""
    db = SessionLocal()
    try:
        knowledge = db.query(TradingKnowledge).filter(TradingKnowledge.id == knowledgeId).first()
        if not knowledge:
            logger.error(f"交易心得不存在 id={knowledgeId}")
            return

        knowledge.status = "processing"
        db.commit()

        startTime = time.time()
        try:
            prompt = buildExtractPrompt(knowledge)
            stdout, stderr, returncode = await callClaude(prompt, EXTRACT_TIMEOUT)
            duration = int(time.time() - startTime)

            if returncode != 0 or not stdout:
                knowledge.status = "failed"
                knowledge.errorMessage = stderr or f"CLI退出码: {returncode}"
                knowledge.processDuration = duration
                logger.error(f"原则提取失败 id={knowledgeId} returncode={returncode}")
                db.commit()
                return

            parsed = parseJson(stdout)
            if not parsed:
                knowledge.status = "failed"
                knowledge.errorMessage = f"JSON解析失败，原始输出前500字：{stdout[:500]}"
                knowledge.processDuration = duration
                logger.error(f"JSON解析失败 id={knowledgeId}")
                db.commit()
                return

            knowledge.status = "completed"
            knowledge.extractedPrinciples = json.dumps(parsed, ensure_ascii=False)
            knowledge.processDuration = duration
            logger.info(f"原则提取完成 id={knowledgeId} duration={duration}s")

        except asyncio.TimeoutError:
            duration = int(time.time() - startTime)
            knowledge.status = "failed"
            knowledge.errorMessage = f"处理超时（{EXTRACT_TIMEOUT}秒）"
            knowledge.processDuration = duration
            logger.error(f"原则提取超时 id={knowledgeId}")

        except Exception as e:
            duration = int(time.time() - startTime)
            knowledge.status = "failed"
            knowledge.errorMessage = str(e)
            knowledge.processDuration = duration
            logger.error(f"原则提取异常 id={knowledgeId}", exc_info=True)

        db.commit()

    except Exception as e:
        logger.error(f"processKnowledgeAsync异常 id={knowledgeId}", exc_info=True)
    finally:
        db.close()


# ==================== 框架合成 ====================

async def rebuildFrameworkAsync() -> None:
    """异步合成交易框架"""
    db = SessionLocal()
    try:
        # 获取所有已完成的心得
        knowledgeList = db.query(TradingKnowledge).filter(
            TradingKnowledge.status == "completed"
        ).all()

        if not knowledgeList:
            logger.error("没有已完成的交易心得，无法合成框架")
            return

        # 构建原则列表
        principlesList = []
        for k in knowledgeList:
            if not k.extractedPrinciples:
                continue
            try:
                principles = json.loads(k.extractedPrinciples)
            except json.JSONDecodeError:
                continue
            principlesList.append({
                "author": k.author or "未知",
                "title": k.title,
                "principles": principles,
            })

        if not principlesList:
            logger.error("没有有效的提取原则，无法合成框架")
            return

        # 获取当前最新框架（如有）
        currentFramework = None
        latestFw = db.query(TradingFramework).filter(
            TradingFramework.status == "completed"
        ).order_by(TradingFramework.version.desc()).first()
        if latestFw and latestFw.frameworkContent:
            try:
                currentFramework = json.loads(latestFw.frameworkContent)
            except json.JSONDecodeError:
                pass

        # 创建新版本
        nextVersion = (latestFw.version + 1) if latestFw else 1
        framework = TradingFramework(
            version=nextVersion,
            status="processing",
            knowledgeCount=len(principlesList),
        )
        db.add(framework)
        db.commit()
        db.refresh(framework)

        startTime = time.time()
        try:
            prompt = buildFrameworkPrompt(principlesList, currentFramework)
            stdout, stderr, returncode = await callClaude(prompt, FRAMEWORK_TIMEOUT)
            duration = int(time.time() - startTime)

            if returncode != 0 or not stdout:
                framework.status = "failed"
                framework.errorMessage = stderr or f"CLI退出码: {returncode}"
                framework.processDuration = duration
                logger.error(f"框架合成失败 version={nextVersion} returncode={returncode}")
                db.commit()
                return

            parsed = parseJson(stdout)
            if not parsed:
                framework.status = "failed"
                framework.errorMessage = f"JSON解析失败，原始输出前500字：{stdout[:500]}"
                framework.processDuration = duration
                logger.error(f"框架合成JSON解析失败 version={nextVersion}")
                db.commit()
                return

            framework.status = "completed"
            framework.frameworkContent = json.dumps(parsed, ensure_ascii=False)
            framework.rawOutput = stdout
            framework.processDuration = duration
            logger.info(f"框架合成完成 version={nextVersion} duration={duration}s sources={len(principlesList)}")

        except asyncio.TimeoutError:
            duration = int(time.time() - startTime)
            framework.status = "failed"
            framework.errorMessage = f"处理超时（{FRAMEWORK_TIMEOUT}秒）"
            framework.processDuration = duration
            logger.error(f"框架合成超时 version={nextVersion}")

        except Exception as e:
            duration = int(time.time() - startTime)
            framework.status = "failed"
            framework.errorMessage = str(e)
            framework.processDuration = duration
            logger.error(f"框架合成异常 version={nextVersion}", exc_info=True)

        db.commit()

    except Exception as e:
        logger.error("rebuildFrameworkAsync异常", exc_info=True)
    finally:
        db.close()


# ==================== CRUD ====================

def getKnowledgeById(db: Session, knowledgeId: int) -> TradingKnowledge | None:
    return db.query(TradingKnowledge).filter(TradingKnowledge.id == knowledgeId).first()


def getKnowledgeList(db: Session, page: int = 1, pageSize: int = 20,
                     status: str | None = None, category: str | None = None) -> tuple[list[TradingKnowledge], int]:
    query = db.query(TradingKnowledge)
    if status:
        query = query.filter(TradingKnowledge.status == status)
    if category:
        query = query.filter(TradingKnowledge.category == category)
    total = query.count()
    items = query.order_by(TradingKnowledge.createdAt.desc()).offset((page - 1) * pageSize).limit(pageSize).all()
    return items, total


def updateKnowledge(db: Session, knowledgeId: int, title: str | None = None,
                    author: str | None = None, content: str | None = None,
                    category: str | None = None) -> TradingKnowledge | None:
    knowledge = getKnowledgeById(db, knowledgeId)
    if not knowledge:
        return None
    if title is not None:
        knowledge.title = title
    if author is not None:
        knowledge.author = author
    if content is not None:
        knowledge.content = content
    if category is not None:
        knowledge.category = category
    db.commit()
    db.refresh(knowledge)
    return knowledge


def deleteKnowledge(db: Session, knowledgeId: int) -> bool:
    knowledge = getKnowledgeById(db, knowledgeId)
    if not knowledge:
        return False
    db.delete(knowledge)
    db.commit()
    return True


# ==================== 框架查询 ====================

def getLatestFramework(db: Session) -> dict | None:
    """获取最新已完成的框架内容"""
    fw = db.query(TradingFramework).filter(
        TradingFramework.status == "completed"
    ).order_by(TradingFramework.version.desc()).first()
    if not fw or not fw.frameworkContent:
        return None
    try:
        return json.loads(fw.frameworkContent)
    except json.JSONDecodeError:
        return None


def getLatestFrameworkRecord(db: Session) -> TradingFramework | None:
    """获取最新已完成的框架记录"""
    return db.query(TradingFramework).filter(
        TradingFramework.status == "completed"
    ).order_by(TradingFramework.version.desc()).first()


def getFrameworkHistory(db: Session, page: int = 1, pageSize: int = 10) -> tuple[list[TradingFramework], int]:
    query = db.query(TradingFramework)
    total = query.count()
    items = query.order_by(TradingFramework.version.desc()).offset((page - 1) * pageSize).limit(pageSize).all()
    return items, total


# ==================== 恢复 ====================

def recoverStuckKnowledge(db: Session) -> int:
    """启动时恢复卡住的心得和框架"""
    count = 0
    for model in [TradingKnowledge, TradingFramework]:
        stuck = db.query(model).filter(model.status.in_(["processing", "pending"])).all()
        for item in stuck:
            item.status = "failed"
            item.errorMessage = "服务重启导致处理中断，请重试"
            count += 1
    if count:
        db.commit()
        logger.info(f"恢复卡住的交易知识记录 count={count}")
    return count
