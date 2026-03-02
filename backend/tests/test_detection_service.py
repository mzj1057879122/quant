"""前高检测算法单元测试"""
import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from app.models.daily_quote import DailyQuote


def makeMockQuotes(prices: list[float], startDate: date | None = None) -> list[DailyQuote]:
    """构造模拟行情数据"""
    if startDate is None:
        startDate = date(2024, 1, 2)

    quotes = []
    currentDate = startDate
    for i, price in enumerate(prices):
        q = DailyQuote()
        q.stockCode = "000001"
        q.tradeDate = currentDate
        q.openPrice = Decimal(str(price * 0.99))
        q.closePrice = Decimal(str(price))
        q.highPrice = Decimal(str(price * 1.01))
        q.lowPrice = Decimal(str(price * 0.98))
        q.volume = 100000
        q.turnover = Decimal("10000000")
        q.changePct = Decimal("0")
        quotes.append(q)
        currentDate += timedelta(days=1)
        # 跳过周末
        if currentDate.weekday() >= 5:
            currentDate += timedelta(days=7 - currentDate.weekday())

    return quotes


class TestMockQuotes(unittest.TestCase):
    def testMakeMockQuotes(self):
        """测试模拟数据生成"""
        prices = [10, 11, 12, 11, 10, 9, 10, 11, 13, 12, 11, 10, 9, 8, 9, 10]
        quotes = makeMockQuotes(prices)
        self.assertEqual(len(quotes), len(prices))
        self.assertEqual(quotes[0].stockCode, "000001")


if __name__ == "__main__":
    unittest.main()
