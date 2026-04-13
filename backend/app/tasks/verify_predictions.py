from datetime import date, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models.backtest_result import BacktestResult
from app.models.daily_quote import DailyQuote
from app.utils.date_helper import isTradingDay, getPreviousTradingDay
from app.utils.logger import setupLogger

logger = setupLogger("task_verify_predictions")


def runVerifyPredictions() -> None:
    """定时任务：验证昨日预测是否正确，更新 is_correct 和 actual_change_pct"""
    today = date.today()
    if not isTradingDay(today):
        logger.info(f"非交易日跳过 date={today}")
        return

    yesterday = getPreviousTradingDay(today)

    db = SessionLocal()
    try:
        # 查昨日未验证的预测记录
        pending = (
            db.execute(
                select(BacktestResult).where(
                    BacktestResult.predictDate == yesterday,
                    BacktestResult.isCorrect.is_(None),
                )
            )
            .scalars()
            .all()
        )

        if not pending:
            logger.info(f"无待验证预测 date={yesterday}")
            return

        updated = 0
        for record in pending:
            try:
                # 查今日行情
                quote = db.execute(
                    select(DailyQuote).where(
                        DailyQuote.stockCode == record.stockCode,
                        DailyQuote.tradeDate == today,
                    )
                ).scalar_one_or_none()

                if quote is None or quote.changePct is None:
                    logger.info(f"今日行情缺失跳过 code={record.stockCode}")
                    continue

                changePct = quote.changePct
                prediction = record.prediction

                if prediction == "看多":
                    isCorrect = 1 if changePct > 0 else 0
                elif prediction == "看空":
                    isCorrect = 1 if changePct < 0 else 0
                else:
                    # 中性不算错
                    isCorrect = 1

                record.isCorrect = isCorrect
                record.actualChangePct = changePct
                updated += 1
            except Exception as e:
                logger.error(
                    f"验证预测异常 id={record.id} code={record.stockCode} 错误={e}",
                    exc_info=True,
                )

        db.commit()
        logger.info(f"预测验证完成 pending={len(pending)} updated={updated}")
    except Exception as e:
        db.rollback()
        logger.error(f"预测验证任务异常 错误={e}", exc_info=True)
    finally:
        db.close()
