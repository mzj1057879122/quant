"""
watchlist 分级脚本：自动为所有股票打 A/B/C 级
运行方式：cd backend && python3 scripts/assign_tiers.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.watchlist import Watchlist

# A 级关键词（sector 包含任一即为 A）
A_SECTOR_KEYWORDS = [
    "光通信", "液冷", "半导体", "军工", "航天", "AI", "人工智能",
    "算力", "低空经济", "内蒙", "自贸", "锂电", "新能源",
]

# A 级强制名单（股票代码）
A_STOCK_CODES = {
    "600498",  # 烽火通信
    "002792",  # 通宇通讯
    "000586",  # 汇源通信
    "600345",  # 长江通信
    "002384",  # 东山精密
    "002975",  # 博杰股份
    "603306",  # 华懋科技
    "002645",  # 华宏科技
    "603538",  # 美诺华
    "002361",  # 神剑股份
}

# C 级关键词（sector 包含任一即为 C）
C_SECTOR_KEYWORDS = ["房地产", "造纸", "农业", "传统"]

# C 级状态
C_STATUSES = {"exited", "warning"}


def classify(stock: Watchlist) -> str:
    code = stock.stockCode.lstrip("0") if stock.stockCode else ""
    sector = stock.sector or ""
    status = stock.status or ""

    # A 级判断
    if stock.stockCode in A_STOCK_CODES:
        return "A"
    if any(kw in sector for kw in A_SECTOR_KEYWORDS):
        return "A"

    # C 级判断
    if status in C_STATUSES:
        return "C"
    if any(kw in sector for kw in C_SECTOR_KEYWORDS):
        return "C"

    return "B"


def main():
    db = SessionLocal()
    try:
        stocks = db.query(Watchlist).order_by(Watchlist.stockCode).all()
        print(f"共 {len(stocks)} 只股票，开始分级...\n")

        counts = {"A": 0, "B": 0, "C": 0}
        for stock in stocks:
            tier = classify(stock)
            stock.tier = tier
            counts[tier] += 1
            sector_display = stock.sector or "（无板块）"
            print(f"  [{tier}] {stock.stockCode} {stock.stockName:<8}  {sector_display}  status={stock.status}")

        db.commit()
        print(f"\n分级完成：A={counts['A']} 只  B={counts['B']} 只  C={counts['C']} 只  合计={len(stocks)} 只")
    except Exception as e:
        db.rollback()
        print(f"错误：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
