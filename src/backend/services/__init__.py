"""后端服务初始化 — 后台线程加载 + 状态追踪"""
import os
from src.backend.core.logger import get_logger

log = get_logger("services")

_brain_service = None
_log_service = None
_perception_service = None

_ready = False
_loading_status: dict = {
    "log": "pending",
    "perception": "pending",
    "brain": "pending",
    "engine": "pending",
}


def boot_services(socketio):
    """在后台线程中依次初始化所有服务并预加载 LLM 引擎"""
    global _brain_service, _log_service, _perception_service, _ready

    # 1. LogService
    _loading_status["log"] = "loading"
    try:
        from src.backend.services.log_service import LogService
        _log_service = LogService(socketio)
        from src.backend.core.logger import redirect_stdio
        redirect_stdio()
        _loading_status["log"] = "ok"
        log.info("LogService 初始化完成")
    except Exception as e:
        _loading_status["log"] = f"error: {e}"
        log.exception("LogService 初始化失败")

    # 2. PerceptionService
    _loading_status["perception"] = "loading"
    try:
        from src.backend.services.perception_service import PerceptionService
        _perception_service = PerceptionService(socketio)
        _loading_status["perception"] = "ok"
        log.info("PerceptionService 初始化完成")
    except Exception as e:
        _loading_status["perception"] = f"error: {e}"
        log.exception("PerceptionService 初始化失败")

    # 3. BrainService
    _loading_status["brain"] = "loading"
    try:
        from src.backend.services.brain_service import BrainService
        _brain_service = BrainService(socketio)
        _loading_status["brain"] = "ok"
        log.info("BrainService 初始化完成")
    except Exception as e:
        _loading_status["brain"] = f"error: {e}"
        log.exception("BrainService 初始化失败")

    # 4. 预加载 LLM 引擎（失败则终止进程）
    _loading_status["engine"] = "loading"
    try:
        if _brain_service:
            _brain_service._ensure_engine()
            _loading_status["engine"] = "ok"
            log.info("LLM 引擎预加载完成")
        else:
            log.error("BrainService 未初始化，无法加载引擎，进程退出")
            os._exit(1)
    except Exception as e:
        log.exception("LLM 引擎预加载失败，进程退出")
        os._exit(1)

    _ready = True
    log.info(f"所有服务加载完成: {_loading_status}")
    socketio.emit("services_ready", _loading_status, namespace="/ws/events")


def is_ready():
    return _ready


def get_status():
    return {"ready": _ready, "services": dict(_loading_status)}


def get_brain():
    return _brain_service


def get_log_service():
    return _log_service


def get_perception():
    return _perception_service


def reload_services():
    """配置变更后重载 BrainService（重建 LLM 引擎）"""
    global _brain_service
    if not _brain_service:
        return
    with _brain_service._engine_lock:
        try:
            _loading_status["engine"] = "reloading"
            if _brain_service.engine:
                import asyncio
                try:
                    asyncio.run_coroutine_threadsafe(
                        _brain_service.engine.shutdown(), _brain_service._loop
                    ).result(timeout=10)
                except Exception:
                    log.warning("旧引擎关闭超时或失败", exc_info=True)
                    try:
                        import torch
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
            _brain_service.engine = None
            _brain_service._do_load_engine()
            _loading_status["engine"] = "ok"
            log.info("LLM 引擎重载完成")
        except Exception as e:
            _loading_status["engine"] = f"error: {e}"
            log.exception("LLM 引擎重载失败")
