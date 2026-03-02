import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config import settings


def setupLogger(name: str) -> logging.Logger:
    """
    创建日志记录器
    成功日志简洁，错误日志详细（含完整堆栈和上下文）
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # 控制台输出：简洁格式
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(getattr(logging, settings.logLevel.upper(), logging.INFO))
    consoleFormat = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    consoleHandler.setFormatter(consoleFormat)
    logger.addHandler(consoleHandler)

    # 文件输出：详细格式（含模块名、函数名、行号）
    logDir = os.path.dirname(settings.logFile)
    if logDir:
        os.makedirs(logDir, exist_ok=True)

    fileHandler = RotatingFileHandler(
        settings.logFile,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fileHandler.setLevel(logging.DEBUG)
    fileFormat = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fileHandler.setFormatter(fileFormat)
    logger.addHandler(fileHandler)

    return logger
