from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.utils.logger import setupLogger

logger = setupLogger("signal_service")


def getSignalList(
    db: Session,
    stockCode: str | None = None,
    signalType: str | None = None,
    startDate: date | None = None,
    endDate: date | None = None,
    page: int = 1,
    pageSize: int = 20,
) -> tuple[list[Signal], int]:
    """获取信号列表（支持筛选和分页）"""
    query = db.query(Signal)

    if stockCode:
        query = query.filter(Signal.stockCode == stockCode)
    if signalType:
        query = query.filter(Signal.signalType == signalType)
    if startDate:
        query = query.filter(Signal.signalDate >= startDate)
    if endDate:
        query = query.filter(Signal.signalDate <= endDate)

    total = query.count()
    items = (
        query.order_by(Signal.signalDate.desc(), Signal.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )
    return items, total


def getUnreadCount(db: Session) -> int:
    """获取未读信号数量"""
    return db.query(Signal).filter(Signal.isRead == 0).count()


def markAsRead(db: Session, signalId: int) -> bool:
    """标记单条信号为已读"""
    signal = db.query(Signal).filter(Signal.id == signalId).first()
    if signal:
        signal.isRead = 1
        db.commit()
        return True
    return False


def markAllAsRead(db: Session) -> int:
    """全部标记为已读，返回更新条数"""
    count = db.query(Signal).filter(Signal.isRead == 0).update({"is_read": 1})
    db.commit()
    logger.info(f"全部已读 count={count}")
    return count


def getSignalStatistics(db: Session, signalDate: date | None = None) -> list[dict]:
    """按信号类型统计"""
    query = db.query(Signal.signalType, func.count(Signal.id).label("count"))

    if signalDate:
        query = query.filter(Signal.signalDate == signalDate)

    results = query.group_by(Signal.signalType).all()
    return [{"signalType": r[0], "count": r[1]} for r in results]


def getUnnotifiedSignals(db: Session) -> list[Signal]:
    """获取未推送的信号"""
    return db.query(Signal).filter(Signal.isNotified == 0).all()


def markAsNotified(db: Session, signalIds: list[int]) -> None:
    """批量标记为已推送"""
    if signalIds:
        db.query(Signal).filter(Signal.id.in_(signalIds)).update(
            {"is_notified": 1}, synchronize_session=False
        )
        db.commit()
