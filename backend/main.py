from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import apiRouter
from app.database import engine, Base, SessionLocal
from app.services.article_service import recoverStuckArticles
from app.services.knowledge_service import recoverStuckKnowledge
from app.services.config_service import initDefaultConfigs
from app.tasks.scheduler import initScheduler, shutdownScheduler
from app.utils.logger import setupLogger

logger = setupLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("应用启动中")

    # 创建数据库表（如果不存在）
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表检查完成")

    # 初始化默认配置 + 恢复卡住的文章
    db = SessionLocal()
    try:
        initDefaultConfigs(db)
        recoverStuckArticles(db)
        recoverStuckKnowledge(db)
    finally:
        db.close()

    # 启动定时任务
    initScheduler()

    yield

    # 关闭时
    shutdownScheduler()
    logger.info("应用已关闭")


app = FastAPI(
    title="量化股票监控系统",
    description="检测股票前高位置，判断突破或突破失败，给出提醒",
    version="1.0.0",
    lifespan=lifespan,
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(apiRouter)
