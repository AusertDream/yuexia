"""WebSocket 事件处理 — Namespace 类注册"""
from flask_socketio import Namespace, emit
from src.backend.core.logger import get_logger

log = get_logger("ws")


class LogsNamespace(Namespace):
    def on_connect(self):
        log.info("客户端连接到 /ws/logs")
        emit("connected", {"status": "ok"})
        try:
            from src.backend.services.log_service import _log_buffer
            for entry in list(_log_buffer):
                emit("log", entry)
        except Exception:
            log.exception("回放日志缓冲失败")

    def on_disconnect(self):
        log.info("客户端断开 /ws/logs")


class EventsNamespace(Namespace):
    def on_connect(self):
        emit("connected", {"status": "ok"})


def register_ws(socketio):
    socketio.on_namespace(LogsNamespace("/ws/logs"))
    socketio.on_namespace(EventsNamespace("/ws/events"))
