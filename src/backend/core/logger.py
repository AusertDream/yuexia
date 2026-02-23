"""统一日志（精简版，仅保留 backend 所需）"""
import logging
import sys

_LOG_FMT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
_DATE_FMT = "%H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
