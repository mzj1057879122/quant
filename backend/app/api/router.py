from fastapi import APIRouter

from app.api.stock import router as stockRouter
from app.api.quote import router as quoteRouter
from app.api.signal import router as signalRouter
from app.api.user_config import router as configRouter
from app.api.system import router as systemRouter
from app.api.article import router as articleRouter
from app.api.knowledge import router as knowledgeRouter
from app.api.heat import router as heatRouter

apiRouter = APIRouter(prefix="/api/v1")

apiRouter.include_router(stockRouter)
apiRouter.include_router(quoteRouter)
apiRouter.include_router(signalRouter)
apiRouter.include_router(configRouter)
apiRouter.include_router(systemRouter)
apiRouter.include_router(articleRouter)
apiRouter.include_router(knowledgeRouter)
apiRouter.include_router(heatRouter)
