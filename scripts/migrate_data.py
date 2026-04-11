"""
数据迁移脚本：将 openclaw 数据导入 quant 数据库

执行：python3 ~/quant/scripts/migrate_data.py

数据源：~/.openclaw/workspace/stock_data/
  - watchlist.json → watchlist 表
  - backtest_v2/*.md → backtest_result 表
  - morning_brief/*.txt → morning_brief 表（source=briefA）
  - morning_brief2/*.txt → morning_brief 表（source=briefB）
"""

import json
import os
import re
import sys
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

# 添加 backend 到 Python 路径，并切换工作目录（config 需要从 backend/ 加载 .env）
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from app.database import SessionLocal
from app.models.watchlist import Watchlist
from app.models.backtest_result import BacktestResult
from app.models.morning_brief import MorningBrief

DATA_DIR = Path.home() / ".openclaw" / "workspace" / "stock_data"

CONFIDENCE_MAP = {
    "🟢": "高",
    "🔵": "高",
    "🟡": "中",
    "🟠": "中",
    "🔴": "低",
}


def parseStockCode(raw: str) -> tuple[str, str]:
    """解析 SH603687 → (stock_code='603687', market='sh')"""
    raw = raw.strip()
    if raw.upper().startswith("SH"):
        return raw[2:], "sh"
    elif raw.upper().startswith("SZ"):
        return raw[2:], "sz"
    return raw, "sh"


def migrateWatchlist(db):
    """从 watchlist.json 导入自选股池"""
    path = DATA_DIR / "watchlist.json"
    if not path.exists():
        print(f"[跳过] {path} 不存在")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stocks = data.get("stocks", [])
    added = 0
    skipped = 0

    for item in stocks:
        raw_code = item.get("code", "")
        stock_code, _ = parseStockCode(raw_code)
        stock_name = item.get("name", "")
        add_reason = item.get("reason")
        anchor_date_str = item.get("added_date")

        existing = db.query(Watchlist).filter(Watchlist.stockCode == stock_code).first()
        if existing:
            skipped += 1
            continue

        w = Watchlist(
            stockCode=stock_code,
            stockName=stock_name,
            addReason=add_reason,
            anchorDate=date.fromisoformat(anchor_date_str) if anchor_date_str else None,
            status="watching",
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
        )
        db.add(w)
        added += 1

    db.commit()
    print(f"[watchlist] 导入完成：新增 {added}，跳过 {skipped}")


def parseConfidence(raw: str) -> str | None:
    """将 🟢/🟡/🔴 转换为 高/中/低"""
    raw = raw.strip()
    for emoji, label in CONFIDENCE_MAP.items():
        if emoji in raw:
            return label
    return None


def parseCorrect(raw: str) -> int | None:
    """解析 ✅/❌ → 1/0/None"""
    raw = raw.strip()
    if "✅" in raw:
        return 1
    if "❌" in raw:
        return 0
    return None


def parseChangePct(raw: str) -> float | None:
    """解析 '涨3.14%' 或 '跌-5.27%' → float"""
    m = re.search(r"[-+]?\d+\.?\d*%", raw)
    if not m:
        # 兼容 C6.68 +1.48% 格式
        m = re.search(r"[+\-]\d+\.?\d*%", raw)
    if m:
        val = m.group().replace("%", "")
        try:
            return float(val)
        except ValueError:
            pass
    return None


def parseBacktestMd(filepath: Path) -> list[dict]:
    """解析单个 backtest md 文件，返回预测记录列表"""
    filename = filepath.stem  # 如 SH603687_大胜达
    parts = filename.split("_", 1)
    if len(parts) < 2:
        return []

    raw_code = parts[0]
    stock_name = parts[1]
    stock_code, _ = parseStockCode(raw_code)

    content = filepath.read_text(encoding="utf-8")

    # 提取启动日锚位
    anchor_match = re.search(r"锚=([0-9.]+)", content)
    anchor_date_match = re.search(r"\*\*启动日：\*\*\s*(\d{4}-\d{2}-\d{2})", content)

    records = []

    for line in content.splitlines():
        line = line.strip()
        # 跳过表头和分隔行
        if not line.startswith("|"):
            continue
        if "日期" in line or ":---" in line:
            continue

        cols = [c.strip() for c in line.split("|")]
        # 去掉首尾空元素
        cols = [c for c in cols if c != ""]

        if len(cols) < 6:
            continue

        date_str = cols[0].strip()
        # 跳过非日期行
        if not re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
            continue
        # 截取日期部分（忽略 "2026-04-13+" 这类带后缀的）
        date_str = date_str[:10]

        try:
            predict_date = date.fromisoformat(date_str)
        except ValueError:
            continue

        technical_signal = cols[1] if len(cols) > 1 else None
        news_signal = cols[2] if len(cols) > 2 else None
        prediction = cols[3] if len(cols) > 3 else None
        confidence_raw = cols[4] if len(cols) > 4 else ""
        actual_raw = cols[5] if len(cols) > 5 else ""
        correct_raw = cols[6] if len(cols) > 6 else ""

        is_correct = parseCorrect(correct_raw)
        # 跳过"待定"记录（没有实际结果）
        if "(待定)" in actual_raw or "(需提供)" in actual_raw:
            continue
        if actual_raw.strip() in ("(待定)", "(需提供)", ""):
            continue

        records.append({
            "stockCode": stock_code,
            "stockName": stock_name,
            "predictDate": predict_date,
            "version": "v2",
            "technicalSignal": technical_signal,
            "newsSignal": news_signal,
            "prediction": prediction,
            "confidence": parseConfidence(confidence_raw),
            "actualResult": actual_raw,
            "isCorrect": is_correct,
            "actualChangePct": parseChangePct(actual_raw),
        })

    return records


def migrateBacktest(db):
    """从 backtest_v2/*.md 导入回测记录"""
    bt_dir = DATA_DIR / "backtest_v2"
    if not bt_dir.exists():
        print(f"[跳过] {bt_dir} 不存在")
        return

    md_files = list(bt_dir.glob("*.md"))
    added = 0
    skipped = 0

    for filepath in sorted(md_files):
        records = parseBacktestMd(filepath)
        for r in records:
            existing = (
                db.query(BacktestResult)
                .filter(
                    BacktestResult.stockCode == r["stockCode"],
                    BacktestResult.predictDate == r["predictDate"],
                    BacktestResult.version == r["version"],
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            row = BacktestResult(
                stockCode=r["stockCode"],
                stockName=r["stockName"],
                predictDate=r["predictDate"],
                version=r["version"],
                technicalSignal=r["technicalSignal"],
                newsSignal=r["newsSignal"],
                prediction=r["prediction"],
                confidence=r["confidence"],
                actualResult=r["actualResult"],
                isCorrect=r["isCorrect"],
                actualChangePct=Decimal(str(r["actualChangePct"])) if r["actualChangePct"] is not None else None,
                createdAt=datetime.now(),
            )
            db.add(row)
            added += 1

    db.commit()
    print(f"[backtest_result] 导入完成：新增 {added}，跳过 {skipped}（共处理 {len(md_files)} 个文件）")


def migrateMorningBrief(db, brief_dir: Path, source: str):
    """从 morning_brief/*.txt 导入盘前纪要"""
    if not brief_dir.exists():
        print(f"[跳过] {brief_dir} 不存在")
        return

    txt_files = list(brief_dir.glob("*.txt"))
    added = 0
    skipped = 0

    for filepath in sorted(txt_files):
        stem = filepath.stem  # 如 2026-03-20
        try:
            brief_date = date.fromisoformat(stem)
        except ValueError:
            continue

        existing = (
            db.query(MorningBrief)
            .filter(MorningBrief.briefDate == brief_date, MorningBrief.source == source)
            .first()
        )
        if existing:
            skipped += 1
            continue

        content = filepath.read_text(encoding="utf-8")

        row = MorningBrief(
            briefDate=brief_date,
            source=source,
            rawContent=content,
            createdAt=datetime.now(),
        )
        db.add(row)
        added += 1

    db.commit()
    print(f"[morning_brief/{source}] 导入完成：新增 {added}，跳过 {skipped}")


def main():
    db = SessionLocal()
    try:
        print("开始数据迁移...")
        migrateWatchlist(db)
        migrateBacktest(db)
        migrateMorningBrief(db, DATA_DIR / "morning_brief", "briefA")
        migrateMorningBrief(db, DATA_DIR / "morning_brief2", "briefB")
        print("数据迁移完成！")
    except Exception as e:
        db.rollback()
        print(f"迁移失败：{e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
