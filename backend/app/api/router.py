from fastapi import APIRouter

from app.api.stock import router as stockRouter
from app.api.quote import router as quoteRouter
from app.api.signal import router as signalRouter
from app.api.user_config import router as configRouter
from app.api.system import router as systemRouter
from app.api.article import router as articleRouter
from app.api.knowledge import router as knowledgeRouter
from app.api.heat import router as heatRouter
from app.api.strong import router as strongRouter
from app.api.watchlist import router as watchlistRouter
from app.api.backtest import router as backtestRouter
from app.api.morning_brief import router as briefRouter

apiRouter = APIRouter(prefix="/api/v1")

apiRouter.include_router(stockRouter)
apiRouter.include_router(quoteRouter)
apiRouter.include_router(signalRouter)
apiRouter.include_router(configRouter)
apiRouter.include_router(systemRouter)
apiRouter.include_router(articleRouter)
apiRouter.include_router(knowledgeRouter)
apiRouter.include_router(heatRouter)
apiRouter.include_router(strongRouter)
apiRouter.include_router(watchlistRouter)
apiRouter.include_router(backtestRouter)
apiRouter.include_router(briefRouter)
