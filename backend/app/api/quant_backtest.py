from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import getDb
from app.models.quant_trade import QuantTrade
from app.services.quant_backtest_service import getRunIds, getRunSummary

router = APIRouter(prefix="/quant-backtest", tags=["量化回测"])


@router.get("/runs")
def listRuns(db: Session = Depends(getDb)):
    """获取所有回测批次列表"""
    runIds = getRunIds(db)
    return {"runs": runIds}


@router.get("/summary")
def getSummary(
    runId: str = Query(..., description="回测批次ID，如 2025_full"),
    db: Session = Depends(getDb),
):
    """获取某批次的汇总统计"""
    runIds = getRunIds(db)
    if runId not in runIds:
        raise HTTPException(status_code=404, detail=f"批次 {runId} 不存在")
    summary = getRunSummary(db, runId)
    return summary


@router.get("/trades")
def listTrades(
    runId: str = Query(..., description="回测批次ID"),
    stockCode: str | None = Query(None, description="股票代码过滤"),
    exitReason: str | None = Query(None, description="出场原因过滤"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    sortBy: str = Query("return_pct", description="排序字段: return_pct / signal_date / hold_days"),
    sortOrder: str = Query("desc", description="asc / desc"),
    db: Session = Depends(getDb),
):
    """获取交易明细（分页，可按股票/出场原因筛选，可按收益率排序）"""
    query = db.query(QuantTrade).filter(QuantTrade.backtestRunId == runId)

    if stockCode:
        query = query.filter(QuantTrade.stockCode == stockCode)
    if exitReason:
        query = query.filter(QuantTrade.exitReason == exitReason)

    # 排序
    sortColMap = {
        "return_pct": QuantTrade.returnPct,
        "signal_date": QuantTrade.signalDate,
        "hold_days": QuantTrade.holdDays,
    }
    sortCol = sortColMap.get(sortBy, QuantTrade.returnPct)
    if sortOrder == "asc":
        query = query.order_by(sortCol.asc())
    else:
        query = query.order_by(sortCol.desc())

    total = query.count()
    items = query.offset((page - 1) * pageSize).limit(pageSize).all()

    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "stockCode": r.stockCode,
                "signalDate": r.signalDate,
                "anchorPrice": float(r.anchorPrice),
                "entryPrice": float(r.entryPrice),
                "entryDate": r.entryDate,
                "exitPrice": float(r.exitPrice) if r.exitPrice is not None else None,
                "exitDate": r.exitDate,
                "exitReason": r.exitReason,
                "returnPct": float(r.returnPct) if r.returnPct is not None else None,
                "holdDays": r.holdDays,
            }
            for r in items
        ],
    }


@router.post("/trigger")
def triggerBacktest(
    runId: str = Query(..., description="批次ID，如 2025_full"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(getDb),
):
    """手动触发回测（后台异步执行）"""
    from app.tasks.run_backtest import runQuantBacktest

    background_tasks.add_task(runQuantBacktest, runId)
    return {"message": f"回测任务已提交 runId={runId}，请稍后查询结果"}
