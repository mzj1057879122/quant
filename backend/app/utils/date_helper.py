from datetime import date, timedelta


def isTradingDay(checkDate: date) -> bool:
    """判断是否为交易日（简单规则：排除周末）"""
    return checkDate.weekday() < 5


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
