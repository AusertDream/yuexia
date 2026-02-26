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
                    msg = msg.rstrip()
                    if not msg:
                        return
                    msg = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', msg)

                    level = self.level

                    # 进度条检测：直接跳过，不记录
                    if '\r' in msg or '%|' in msg or 'it/s' in msg or 'ETA' in msg:
                        return
                    if re.search(r'\d+%', msg) and ('|' in msg or '\u2588' in msg or '\u258f' in msg or '/' in msg):
                        return

                    # stderr 弃用警告降级为 WARNING
                    if level >= logging.ERROR:
                        _warn_kw = ('DeprecationWarning', 'FutureWarning', 'UserWarning',
                                    'deprecated', 'will be removed', 'is deprecated')
                        if any(kw in msg for kw in _warn_kw):
                            level = logging.WARNING

                    self.logger.log(level, msg)
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
