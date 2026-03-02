import akshare as ak
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.utils.logger import setupLogger

logger = setupLogger("stock_service")


def syncStockList(db: Session) -> int:
    """从akshare同步A股股票列表（沪深），返回新增数量"""
    try:
        stockList = []

        # 分开拉取沪市（主板A股 + 科创板）
        for symbol in ["主板A股", "科创板"]:
            try:
                df = ak.stock_info_sh_name_code(symbol)
                for _, row in df.iterrows():
                    stockList.append({
                        "code": str(row["证券代码"]).strip(),
                        "name": str(row["证券简称"]).strip(),
                        "market": "sh",
                    })
            except Exception as e:
                logger.error(f"沪市{symbol}同步失败 错误={e}", exc_info=True)

        # 拉取深市A股
        try:
            df = ak.stock_info_sz_name_code("A股列表")
            for _, row in df.iterrows():
                stockList.append({
                    "code": str(row["A股代码"]).strip(),
                    "name": str(row["A股简称"]).strip(),
                    "market": "sz",
                })
        except Exception as e:
            logger.error(f"深市A股同步失败 错误={e}", exc_info=True)

        newCount = 0
        for item in stockList:
            existing = db.query(Stock).filter(Stock.stockCode == item["code"]).first()
            if existing:
                if existing.stockName != item["name"]:
                    existing.stockName = item["name"]
            else:
                stock = Stock(stockCode=item["code"], stockName=item["name"], market=item["market"])
                db.add(stock)
                newCount += 1

        db.commit()
        logger.info(f"股票列表同步完成 新增={newCount}")
        return newCount

    except Exception as e:
        db.rollback()
        logger.error(f"股票列表同步失败 错误={e}", exc_info=True)
        raise


def getStockList(
    db: Session,
    keyword: str | None = None,
    page: int = 1,
    pageSize: int = 20,
) -> tuple[list[Stock], int]:
    """获取股票列表（支持搜索和分页）"""
    query = db.query(Stock).filter(Stock.isActive == 1)

    if keyword:
        query = query.filter(
            (Stock.stockCode.contains(keyword)) | (Stock.stockName.contains(keyword))
        )

    total = query.count()
    items = query.order_by(Stock.stockCode).offset((page - 1) * pageSize).limit(pageSize).all()
    return items, total


def getStockByCode(db: Session, stockCode: str) -> Stock | None:
    """根据股票代码获取股票信息"""
    return db.query(Stock).filter(Stock.stockCode == stockCode).first()


def getStocksByCodeList(db: Session, stockCodes: list[str]) -> list[Stock]:
    """根据代码列表批量获取股票信息"""
    return db.query(Stock).filter(Stock.stockCode.in_(stockCodes)).all()
