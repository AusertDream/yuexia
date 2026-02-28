"""系统状态 API + Swagger 文档"""
import os
import base64
import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from src.backend.core.logger import get_logger

log = get_logger("api.system")

# 预热 psutil cpu_percent，interval=None 首次调用返回 0.0
psutil.cpu_percent(interval=None)

system_router = APIRouter()

API_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "YueXia API", "version": "1.0.0"},
    "paths": {
        "/api/chat/stream": {
            "post": {
                "summary": "LLM 流式聊天 (SSE)",
                "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"text": {"type": "string"}}}}}},
                "responses": {"200": {"description": "SSE stream of chunks"}},
            }
        },
        "/api/config": {
            "get": {"summary": "获取配置", "responses": {"200": {"description": "YAML config as JSON"}}},
            "put": {"summary": "更新配置", "responses": {"200": {"description": "ok"}}},
        },
        "/api/sessions": {
            "get": {"summary": "会话列表", "responses": {"200": {"description": "sessions array"}}},
            "post": {"summary": "新建会话", "responses": {"200": {"description": "session_id"}}},
        },
        "/api/sessions/{sid}": {
            "put": {"summary": "重命名会话", "responses": {"200": {"description": "ok"}}},
            "delete": {"summary": "删除会话", "responses": {"200": {"description": "ok"}}},
        },
        "/api/sessions/{sid}/switch": {
            "post": {"summary": "切换会话", "responses": {"200": {"description": "messages"}}},
        },
        "/api/system/status": {
            "get": {"summary": "系统状态", "responses": {"200": {"description": "CPU/RAM/GPU info"}}},
        },
    },
}


def _gpu_info():
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            return {"name": g.name, "mem_used": round(g.memoryUsed / 1024, 1), "mem_total": round(g.memoryTotal / 1024, 1), "load": round(g.load * 100)}
    except Exception:
        pass
    return None


@system_router.get("/api/system/status")
async def system_status():
    from src.backend.services import get_status, get_brain
    mem = psutil.virtual_memory()
    svc = get_status()
    brain = get_brain()
    return JSONResponse(content={
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_used": round(mem.used / (1024 ** 3), 1),
        "ram_total": round(mem.total / (1024 ** 3), 1),
        "gpu": _gpu_info(),
        "services_ready": svc["ready"],
        "loading_status": svc["services"],
        "inference_speed": brain._last_inference_speed if brain else 0,
    })


@system_router.get("/api/docs/spec")
async def api_spec():
    return JSONResponse(content=API_SPEC)


@system_router.get("/api/docs")
async def api_docs():
    return HTMLResponse("""<!DOCTYPE html><html><head><title>YueXia API Docs</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head><body><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url:"/api/docs/spec",dom_id:"#swagger-ui"})</script>
</body></html>""")


@system_router.get("/api/screenshot")
async def screenshot():
    from src.backend.core.config import get_config
    cfg = get_config()
    if not cfg.get("action", {}).get("screen", {}).get("enabled", False):
        return JSONResponse(content={"error": "screenshot disabled"}, status_code=403)
    try:
        import mss
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[1])
            from PIL import Image
            import io
            pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            pil.save(buf, format="JPEG", quality=60)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return JSONResponse(content={"image": f"data:image/jpeg;base64,{b64}"})
    except Exception as e:
        log.exception("截图失败")
        return JSONResponse(content={"error": str(e)}, status_code=500)
