import asyncio
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import getDb
from app.schemas.article import (
    ArticleSubmitRequest,
    ArticleUrlRequest,
    BatchUpdateDateRequest,
    ArticleResponse,
    ArticleListResponse,
    ArticleStatusResponse,
)
from app.schemas.daily_summary import (
    DailySummaryResponse,
    DailySummaryListResponse,
    DailySummaryStatusResponse,
)
from app.services import article_service

router = APIRouter(prefix="/articles", tags=["知识学习"])


# ==================== 文章接口 ====================

@router.post("", response_model=ArticleStatusResponse)
async def submitArticle(
    req: ArticleSubmitRequest,
    db: Session = Depends(getDb),
):
    """提交文章进行单篇分析"""
    article = article_service.submitArticle(db, req.title, req.author, req.content, req.source, req.articleDate)
    asyncio.create_task(article_service.processArticleAsync(article.id))
    return article


@router.post("/from-url", response_model=ArticleResponse)
async def submitFromUrl(
    req: ArticleUrlRequest,
    db: Session = Depends(getDb),
):
    """通过URL提取文章并提交分析"""
    try:
        data = article_service.extractFromUrl(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"提取失败: {e}")

    # 如果用户指定了日期，优先使用用户指定的日期
    finalDate = req.articleDate if req.articleDate else data["articleDate"]

    article = article_service.submitArticle(
        db,
        title=data["title"],
        author=data["author"],
        content=data["content"],
        source=data["source"],
        articleDate=finalDate,
        sourceUrl=data["sourceUrl"],
    )
    asyncio.create_task(article_service.processArticleAsync(article.id))
    return article


@router.get("/{articleId}", response_model=ArticleStatusResponse)
def getArticleStatus(
    articleId: int,
    db: Session = Depends(getDb),
):
    """查询文章处理状态"""
    article = article_service.getArticleById(db, articleId)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


@router.get("", response_model=ArticleListResponse)
def listArticles(
    status: str | None = Query(None),
    articleDate: date | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(getDb),
):
    """获取文章列表"""
    items, total = article_service.getArticleList(db, status, articleDate, page, pageSize)
    return ArticleListResponse(total=total, items=items)


@router.post("/{articleId}/retry", response_model=ArticleStatusResponse)
async def retryArticle(
    articleId: int,
    db: Session = Depends(getDb),
):
    """重试失败的文章"""
    article = article_service.getArticleById(db, articleId)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status != "failed":
        raise HTTPException(status_code=400, detail="只能重试失败的文章")

    article.status = "pending"
    article.errorMessage = None
    article.resultSummary = None
    article.processDuration = None
    db.commit()
    db.refresh(article)

    asyncio.create_task(article_service.processArticleAsync(article.id))
    return article


@router.delete("/{articleId}")
def deleteArticle(
    articleId: int,
    db: Session = Depends(getDb),
):
    """删除文章"""
    article = article_service.getArticleById(db, articleId)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"message": "已删除"}


@router.put("/batch-update-date")
def batchUpdateDate(
    req: BatchUpdateDateRequest,
    db: Session = Depends(getDb),
):
    """批量修改文章日期"""
    count = article_service.batchUpdateArticleDate(db, req.articleIds, req.articleDate)
    return {"message": f"已更新 {count} 篇文章日期", "count": count}


# ==================== 每日汇总接口 ====================

@router.post("/daily-summary", response_model=DailySummaryStatusResponse)
async def triggerDailySummary(
    summaryDate: date = Query(default=None),
    db: Session = Depends(getDb),
):
    """触发生成每日综合策略"""
    targetDate = summaryDate or date.today()

    # 检查当日是否有已完成的文章
    articles, count = article_service.getArticleList(db, status="completed", articleDate=targetDate)
    if not articles:
        raise HTTPException(status_code=400, detail=f"{targetDate} 没有已完成分析的文章")

    # 获取或创建汇总记录
    summary = article_service.getDailySummary(db, targetDate)
    if summary and summary.status == "processing":
        raise HTTPException(status_code=400, detail="汇总正在生成中，请稍候")

    if summary:
        summary.status = "pending"
        summary.errorMessage = None
        summary.consensus = None
        summary.divergence = None
        summary.stockViews = None
        summary.sectorViews = None
        summary.strategy = None
        summary.evolution = None
        summary.rawOutput = None
        summary.processDuration = None
        db.commit()
        db.refresh(summary)
    else:
        summary = article_service.getDailySummary(db, targetDate)

    asyncio.create_task(article_service.generateDailySummaryAsync(targetDate))
    return summary or DailySummaryStatusResponse(id=0, summaryDate=targetDate, status="pending")


@router.get("/daily-summary/{summaryDate}", response_model=DailySummaryResponse)
def getDailySummary(
    summaryDate: date,
    db: Session = Depends(getDb),
):
    """查询某日综合策略"""
    summary = article_service.getDailySummary(db, summaryDate)
    if not summary:
        raise HTTPException(status_code=404, detail=f"{summaryDate} 暂无汇总")
    return summary


@router.get("/daily-summaries", response_model=DailySummaryListResponse)
def listDailySummaries(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    db: Session = Depends(getDb),
):
    """获取每日汇总列表"""
    items, total = article_service.getDailySummaryList(db, page, pageSize)
    return DailySummaryListResponse(total=total, items=items)
