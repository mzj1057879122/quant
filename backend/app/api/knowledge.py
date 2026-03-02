import asyncio

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import getDb
from app.schemas.knowledge import (
    KnowledgeSubmitRequest,
    KnowledgeUrlRequest,
    KnowledgeUpdateRequest,
    KnowledgeResponse,
    KnowledgeListResponse,
    KnowledgeStatusResponse,
    FrameworkResponse,
    FrameworkListResponse,
)
from app.services import knowledge_service
from app.services.article_service import extractFromUrl

router = APIRouter(prefix="/knowledge", tags=["交易框架"])


# ==================== 心得接口 ====================

@router.post("", response_model=KnowledgeStatusResponse)
async def submitKnowledge(
    req: KnowledgeSubmitRequest,
    db: Session = Depends(getDb),
):
    """提交交易心得，触发异步提取原则"""
    knowledge = knowledge_service.submitKnowledge(
        db, req.title, req.author, req.content, req.source, req.category, req.sourceUrl
    )
    asyncio.create_task(knowledge_service.processKnowledgeAsync(knowledge.id))
    return knowledge


@router.post("/from-url", response_model=KnowledgeResponse)
async def submitFromUrl(
    req: KnowledgeUrlRequest,
    db: Session = Depends(getDb),
):
    """通过URL提取后提交交易心得"""
    try:
        data = extractFromUrl(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"提取失败: {e}")

    knowledge = knowledge_service.submitKnowledge(
        db,
        title=data["title"],
        author=data["author"],
        content=data["content"],
        source=data["source"],
        category=req.category,
        sourceUrl=data["sourceUrl"],
    )
    asyncio.create_task(knowledge_service.processKnowledgeAsync(knowledge.id))
    return knowledge


@router.get("", response_model=KnowledgeListResponse)
def listKnowledge(
    status: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(getDb),
):
    """获取交易心得列表"""
    items, total = knowledge_service.getKnowledgeList(db, page, pageSize, status, category)
    return KnowledgeListResponse(total=total, items=items)


@router.get("/{knowledgeId}", response_model=KnowledgeResponse)
def getKnowledge(
    knowledgeId: int,
    db: Session = Depends(getDb),
):
    """获取单篇交易心得"""
    knowledge = knowledge_service.getKnowledgeById(db, knowledgeId)
    if not knowledge:
        raise HTTPException(status_code=404, detail="交易心得不存在")
    return knowledge


@router.put("/{knowledgeId}", response_model=KnowledgeResponse)
def updateKnowledge(
    knowledgeId: int,
    req: KnowledgeUpdateRequest,
    db: Session = Depends(getDb),
):
    """编辑交易心得"""
    knowledge = knowledge_service.updateKnowledge(
        db, knowledgeId, req.title, req.author, req.content, req.category
    )
    if not knowledge:
        raise HTTPException(status_code=404, detail="交易心得不存在")
    return knowledge


@router.post("/{knowledgeId}/retry", response_model=KnowledgeStatusResponse)
async def retryKnowledge(
    knowledgeId: int,
    db: Session = Depends(getDb),
):
    """重试失败的心得提取"""
    knowledge = knowledge_service.getKnowledgeById(db, knowledgeId)
    if not knowledge:
        raise HTTPException(status_code=404, detail="交易心得不存在")
    if knowledge.status != "failed":
        raise HTTPException(status_code=400, detail="只能重试失败的心得")

    knowledge.status = "pending"
    knowledge.errorMessage = None
    knowledge.extractedPrinciples = None
    knowledge.processDuration = None
    db.commit()
    db.refresh(knowledge)

    asyncio.create_task(knowledge_service.processKnowledgeAsync(knowledge.id))
    return knowledge


@router.post("/{knowledgeId}/re-extract", response_model=KnowledgeStatusResponse)
async def reExtractKnowledge(
    knowledgeId: int,
    db: Session = Depends(getDb),
):
    """编辑后重新提取原则"""
    knowledge = knowledge_service.getKnowledgeById(db, knowledgeId)
    if not knowledge:
        raise HTTPException(status_code=404, detail="交易心得不存在")

    knowledge.status = "pending"
    knowledge.errorMessage = None
    knowledge.extractedPrinciples = None
    knowledge.processDuration = None
    db.commit()
    db.refresh(knowledge)

    asyncio.create_task(knowledge_service.processKnowledgeAsync(knowledge.id))
    return knowledge


@router.delete("/{knowledgeId}")
def deleteKnowledge(
    knowledgeId: int,
    db: Session = Depends(getDb),
):
    """删除交易心得"""
    if not knowledge_service.deleteKnowledge(db, knowledgeId):
        raise HTTPException(status_code=404, detail="交易心得不存在")
    return {"message": "已删除"}


# ==================== 框架接口 ====================

@router.post("/framework/rebuild", response_model=FrameworkResponse)
async def rebuildFramework(
    db: Session = Depends(getDb),
):
    """重建交易框架"""
    # 检查是否有已完成的心得
    items, total = knowledge_service.getKnowledgeList(db, status="completed")
    if not items:
        raise HTTPException(status_code=400, detail="没有已完成提取的交易心得")

    asyncio.create_task(knowledge_service.rebuildFrameworkAsync())

    # 返回一个临时状态
    latestFw = knowledge_service.getLatestFrameworkRecord(db)
    nextVersion = (latestFw.version + 1) if latestFw else 1
    return FrameworkResponse(
        id=0, version=nextVersion, status="processing",
        knowledgeCount=total, createdAt=__import__("datetime").datetime.now()
    )


@router.get("/framework/latest", response_model=FrameworkResponse | None)
def getLatestFramework(
    db: Session = Depends(getDb),
):
    """获取最新框架"""
    fw = knowledge_service.getLatestFrameworkRecord(db)
    if not fw:
        return None
    return fw


@router.get("/framework/history", response_model=FrameworkListResponse)
def getFrameworkHistory(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    db: Session = Depends(getDb),
):
    """获取框架版本历史"""
    items, total = knowledge_service.getFrameworkHistory(db, page, pageSize)
    return FrameworkListResponse(total=total, items=items)
