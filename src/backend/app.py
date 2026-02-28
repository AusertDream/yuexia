"""FastAPI 应用入口"""
import os
import asyncio
import logging
import time
from collections import defaultdict

_env_root = os.environ.get("YUEXIA_ROOT", "").strip()
ROOT_DIR = _env_root if _env_root else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

log = logging.getLogger(__name__)

# Socket.IO ASGI 模式
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


def create_app():
    app = FastAPI(title="YueXia API")

    # TTS 音频静态文件
    tts_dir = os.path.join(ROOT_DIR, "data", "tts_output")
    os.makedirs(tts_dir, exist_ok=True)

    @app.get("/audio/{filename:path}")
    async def serve_audio(filename: str):
        filepath = os.path.join(tts_dir, filename)
        if os.path.isfile(filepath):
            return FileResponse(filepath)
        return JSONResponse({"error": "文件不存在"}, status_code=404)

    # 加载配置
    config_path = os.path.join(ROOT_DIR, "config", "config.yaml")
    from src.backend.core.config import load_config
    load_config(config_path)

    from src.backend.core.config import get as cfg_get

    # Security: log_level
    log_level = cfg_get("security.log_level", "INFO")
    logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))

    # Security: CORS allowed_origins
    origins = cfg_get("security.allowed_origins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    from src.backend.api.chat import chat_router
    from src.backend.api.config_api import config_router
    from src.backend.api.session import session_router
    from src.backend.api.system import system_router
    from src.backend.api.asr_api import asr_router
    app.include_router(chat_router)
    app.include_router(config_router)
    app.include_router(session_router)
    app.include_router(system_router)
    app.include_router(asr_router)

    # Security: request size limit & rate limit
    if cfg_get("security.api_access_control", False):
        _rate_counts: dict[str, list[float]] = defaultdict(list)

        @app.middleware("http")
        async def security_middleware(request: Request, call_next):
            max_body = cfg_get("security.max_request_size_mb", 10) * 1024 * 1024
            rpm = cfg_get("security.rate_limit_per_minute", 60)
            cl = request.headers.get("content-length")
            if cl and int(cl) > max_body:
                return JSONResponse({"error": "请求体过大"}, status_code=413)
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            timestamps = [t for t in _rate_counts.get(ip, []) if now - t < 60]
            if len(timestamps) >= rpm:
                _rate_counts[ip] = timestamps
                return JSONResponse({"error": "请求过于频繁"}, status_code=429)
            timestamps.append(now)
            if timestamps:
                _rate_counts[ip] = timestamps
            elif ip in _rate_counts:
                del _rate_counts[ip]
            return await call_next(request)

    # 全局异常处理
    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception):
        log.exception("服务器内部错误")
        return JSONResponse({"error": "服务器内部错误", "detail": str(exc)}, status_code=500)

    return app


# Socket.IO 事件处理
@sio.on("connect", namespace="/ws/events")
async def events_connect(sid, environ):
    await sio.emit("connected", {"status": "ok"}, room=sid, namespace="/ws/events")


@sio.on("connect", namespace="/ws/logs")
async def logs_connect(sid, environ):
    await sio.emit("connected", {"status": "ok"}, room=sid, namespace="/ws/logs")
    try:
        from src.backend.services.log_service import _log_buffer
        for entry in list(_log_buffer):
            await sio.emit("log", entry, room=sid, namespace="/ws/logs")
    except Exception:
        log.exception("回放日志缓冲失败")


app = create_app()
# 将 FastAPI 挂载到 Socket.IO ASGI 应用
asgi_app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn
    from src.backend.core.config import get
    port = get("server.backend_port", 5000)

    # 写入运行时端口文件
    runtime_dir = os.path.join(ROOT_DIR, ".runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    with open(os.path.join(runtime_dir, "backend_port"), "w") as f:
        f.write(str(port))

    # 后台启动服务
    import threading
    from src.backend.services import boot_services
    threading.Thread(target=boot_services, args=(sio,), daemon=True).start()

    uvicorn.run(asgi_app, host="0.0.0.0", port=port, log_level="info")
