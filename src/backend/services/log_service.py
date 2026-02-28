"""日志服务 - WebSocket 广播 + JSON文件 + TTS日志尾随"""
import json
import logging
import os
import threading
import time
import traceback
from collections import deque
from pathlib import Path

from src.backend.core.logger import _LOG_FMT, _DATE_FMT, _original_stderr, WerkzeugFilter

# 全局日志缓冲，供客户端连接时回放
_log_buffer: deque = deque(maxlen=200)


class WebSocketLogHandler(logging.Handler):
    def __init__(self, socketio):
        super().__init__()
        self.socketio = socketio
        self.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))

    def emit(self, record):
        try:
            entry = {
                "time": self.formatter.formatTime(record, _DATE_FMT),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
            }
            _log_buffer.append(entry)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.socketio.emit("log", entry, namespace="/ws/logs"),
                        loop
                    )
                else:
                    loop.run_until_complete(self.socketio.emit("log", entry, namespace="/ws/logs"))
            except RuntimeError:
                pass
        except Exception as e:
            print(f"[LogHandler] {e}", file=_original_stderr)


class JsonFileLogHandler(logging.Handler):
    def __init__(self, log_dir):
        super().__init__()
        os.makedirs(log_dir, exist_ok=True)
        self._file = open(os.path.join(log_dir, "structured.jsonl"), "a", encoding="utf-8")
        self.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT))

    def emit(self, record):
        try:
            exc = None
            if record.exc_info and record.exc_info[0] is not None:
                exc = "".join(traceback.format_exception(*record.exc_info))
            entry = {
                "time": self.formatter.formatTime(record, _DATE_FMT),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
                "filename": record.filename,
                "lineno": record.lineno,
                "funcName": record.funcName,
                "exc_info": exc,
            }
            self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._file.flush()
        except Exception as e:
            print(f"[JsonLogHandler] {e}", file=_original_stderr)

    def close(self):
        self._file.close()
        super().close()


class TtsLogTailer:
    def __init__(self, log_path):
        self.log_path = log_path
        self._logger = logging.getLogger("tts")

    def start(self):
        t = threading.Thread(target=self._tail, daemon=True)
        t.start()

    # tqdm 进度条特征字符，用于过滤刷屏行
    _PROGRESS_CHARS = set("█▏▎▍▌▋▊▉")

    def _tail(self):
        while not os.path.exists(self.log_path):
            time.sleep(2)
        with open(self.log_path, "rb") as f:
            f.seek(0, 2)  # seek to end
            buf = b""
            while True:
                chunk = f.read(4096)
                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        raw_line, buf = buf.split(b"\n", 1)
                        line = self._decode_line(raw_line)
                        line = line.rstrip()
                        if not line:
                            continue
                        if "%|" in line or "it/s" in line or "s/it" in line or "\r" in line:
                            continue
                        if any(c in self._PROGRESS_CHARS for c in line):
                            continue
                        self._logger.info(line)
                else:
                    time.sleep(0.5)

    @staticmethod
    def _decode_line(raw: bytes) -> str:
        """先尝试 UTF-8 解码，失败则 fallback 到 GBK"""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("gbk", errors="replace")


class LogService:
    def __init__(self, socketio):
        self.socketio = socketio
        root = logging.getLogger()

        # WebSocket handler
        ws_handler = WebSocketLogHandler(socketio)
        ws_handler.setLevel(logging.INFO)
        ws_handler.addFilter(WerkzeugFilter())
        root.addHandler(ws_handler)

        # JSON file handler - 找 logs/ 下最新子目录
        log_dir = self._find_latest_log_dir()
        if log_dir:
            json_handler = JsonFileLogHandler(log_dir)
            json_handler.setLevel(logging.INFO)
            root.addHandler(json_handler)

        root.setLevel(logging.INFO)

        # TTS log tailer
        tts_log = os.environ.get("YUEXIA_TTS_LOG")
        if not tts_log and log_dir:
            tts_log = os.path.join(log_dir, "tts.log")
        if tts_log:
            self.tts_tailer = TtsLogTailer(tts_log)
            self.tts_tailer.start()

    @staticmethod
    def _find_latest_log_dir():
        env_root = os.environ.get("YUEXIA_ROOT", "").strip()
        if env_root:
            logs_root = Path(env_root) / "logs"
        else:
            logs_root = Path("logs")
        if not logs_root.is_dir():
            return None
        subdirs = sorted([d for d in logs_root.iterdir() if d.is_dir()])
        return str(subdirs[-1]) if subdirs else None
