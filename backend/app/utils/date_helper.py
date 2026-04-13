from datetime import date, timedelta

# A股节假日列表（硬编码，需每年维护）
_A_SHARE_HOLIDAYS = {
    # 2025年
    date(2025, 1, 1),   # 元旦
    date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
    date(2025, 1, 31), date(2025, 2, 3), date(2025, 2, 4),  # 春节
    date(2025, 4, 4),   # 清明节
    date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 5),   # 劳动节
    date(2025, 5, 31),  # 端午节
    date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3),
    date(2025, 10, 6), date(2025, 10, 7), date(2025, 10, 8),  # 国庆节
    # 2026年
    date(2026, 1, 1),   # 元旦
    date(2026, 2, 17), date(2026, 2, 18), date(2026, 2, 19),
    date(2026, 2, 20), date(2026, 2, 23), date(2026, 2, 24),  # 春节
    date(2026, 4, 6),   # 清明节
    date(2026, 5, 1), date(2026, 5, 4), date(2026, 5, 5),   # 劳动节
    date(2026, 6, 19),  # 端午节
    date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5),
    date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8),  # 国庆节
}


def isTradingDay(checkDate: date) -> bool:
    """判断是否为交易日（排除周末和A股节假日）"""
    if checkDate.weekday() >= 5:
        return False
    return checkDate not in _A_SHARE_HOLIDAYS


def getLastTradingDay(currentDate: date | None = None) -> date:
    """获取最近一个交易日"""
    if currentDate is None:
        currentDate = date.today()
    checkDate = currentDate
    # 如果当前不是交易日，往前推
    while not isTradingDay(checkDate):
        checkDate -= timedelta(days=1)
    return checkDate


def getPreviousTradingDay(currentDate: date | None = None) -> date:
    """获取前一个交易日"""
    if currentDate is None:
        currentDate = date.today()
    checkDate = currentDate - timedelta(days=1)
    while not isTradingDay(checkDate):
        checkDate -= timedelta(days=1)
    return checkDate
