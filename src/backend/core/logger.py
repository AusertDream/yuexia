"""统一日志（精简版，仅保留 backend 所需）"""
import io
import logging
import re
import sys
import threading

_LOG_FMT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
_DATE_FMT = "%H:%M:%S"

_original_stdout = sys.stdout
_original_stderr = sys.stderr
_root_configured = False


def _setup_root_logger():
    global _root_configured
    if _root_configured:
        return
    root = logging.getLogger()
    stream = io.TextIOWrapper(_original_stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    _root_configured = True


def get_logger(name: str, level: int = None) -> logging.Logger:
    _setup_root_logger()
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


class WerkzeugFilter(logging.Filter):
    _http_re = re.compile(r'^[\d.]+ - - \[')
    def filter(self, record):
        return not (record.name == 'werkzeug' and self._http_re.match(record.getMessage()))


class StreamToLogger:
    def __init__(self, logger: logging.Logger, level: int, original_stream):
        self.logger = logger
        self.level = level
        self.original_stream = original_stream
        self._local = threading.local()

    def write(self, msg):
        if msg and msg.strip():
            if not getattr(self._local, 'redirecting', False):
                self._local.redirecting = True
                try:
                    level = self.level
                    if level >= logging.ERROR and ('%|' in msg or 'it/s' in msg):
                        level = logging.DEBUG
                    self.logger.log(level, msg.rstrip())
                finally:
                    self._local.redirecting = False
                return
        self.original_stream.write(msg)

    def flush(self):
        self.original_stream.flush()

    def fileno(self):
        return self.original_stream.fileno()


def redirect_stdio():
    sys.stdout = StreamToLogger(
        logging.getLogger("stdout"), logging.INFO, _original_stdout
    )
    sys.stderr = StreamToLogger(
        logging.getLogger("stderr"), logging.ERROR, _original_stderr
    )
