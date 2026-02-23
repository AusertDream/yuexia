"""日志服务 - WebSocket 广播 + 历史缓冲"""
import sys
import logging
from collections import deque
from src.backend.core.logger import _LOG_FMT, _DATE_FMT

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
            self.socketio.emit("log", entry, namespace="/ws/logs")
        except Exception as e:
            print(f"[LogHandler] {e}", file=sys.stderr)


class LogService:
    def __init__(self, socketio):
        self.socketio = socketio
        handler = WebSocketLogHandler(socketio)
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
