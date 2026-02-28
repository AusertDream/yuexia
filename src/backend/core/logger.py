"""统一日志（精简版，仅保留 backend 所需）"""
import io
import os
import logging
import re
import sys
import threading
from pathlib import Path

_LOG_FMT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
_DATE_FMT = "%H:%M:%S"

_original_stdout = sys.stdout
_original_stderr = sys.stderr
_root_configured = False


def _find_log_dir():
    """查找 logs 目录下最新的子目录，优先使用 YUEXIA_ROOT 绝对路径"""
    from datetime import datetime
    env_root = os.environ.get("YUEXIA_ROOT", "").strip()
    if env_root:
        logs_root = Path(env_root) / "logs"
    else:
        # 通过当前文件路径推算项目根目录: src/backend/core/logger.py -> 往上4级
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        logs_root = project_root / "logs"
    if not logs_root.is_dir():
        try:
            today = datetime.now().strftime("%Y%m%d")
            log_dir = logs_root / today
            log_dir.mkdir(parents=True, exist_ok=True)
            return str(log_dir)
        except OSError:
            return None
    subdirs = sorted([d for d in logs_root.iterdir() if d.is_dir()])
    if not subdirs:
        try:
            today = datetime.now().strftime("%Y%m%d")
            log_dir = logs_root / today
            log_dir.mkdir(exist_ok=True)
            return str(log_dir)
        except OSError:
            return None
    return str(subdirs[-1])


def _setup_root_logger():
    global _root_configured
    if _root_configured:
        return
    root = logging.getLogger()
    fmt = logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT)

    stream = io.TextIOWrapper(_original_stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(fmt)
    root.addHandler(handler)

    # 直接写入 backend.log，绕过 conda run 的管道缓冲
    log_dir = _find_log_dir()
    if log_dir:
        try:
            fh = logging.FileHandler(
                Path(log_dir) / "backend.log", encoding="utf-8"
            )
            fh.setLevel(logging.INFO)
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except OSError:
            pass

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
