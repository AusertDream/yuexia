"""统一日志"""
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


class QueueLogHandler(logging.Handler):
    """将日志记录发送到 mp.Queue，供 Face 进程的 ConsolePage 显示"""

    def __init__(self, queue):
        super().__init__()
        self._queue = queue
        self.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))

    def emit(self, record):
        try:
            self._queue.put_nowait(self.format(record))
        except Exception:
            pass


def setup_queue_logging(queue, level: int = logging.INFO):
    """在子进程中调用，将 root logger 的日志转发到 queue"""
    root = logging.getLogger()
    root.addHandler(QueueLogHandler(queue))
    root.setLevel(level)
