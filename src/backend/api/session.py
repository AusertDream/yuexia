"""会话管理 API"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from src.backend.core.logger import get_logger

log = get_logger("api.session")

session_router = APIRouter(prefix="/api/sessions")


def _brain():
    from src.backend.services import get_brain
    b = get_brain()
    if b is None:
        raise HTTPException(status_code=503, detail="服务未就绪")
    return b


def _check_sid(brain, sid):
    if not any(e["id"] == sid for e in brain.session_mgr.index):
        return JSONResponse(content={"error": "会话不存在"}, status_code=404)
    return None


@session_router.get("")
async def list_sessions():
    b = _brain()
    return JSONResponse(content={
        "sessions": b.session_mgr.list_sessions(),
        "current_id": b.session_mgr.current_id,
    })


@session_router.post("")
async def create_session():
    b = _brain()
    b.session_mgr.save_messages(b.history)
    sid = b.session_mgr.create()
    b.history = []
    b.latest_screenshot = None
    log.info(f"创建会话: {sid}")
    return JSONResponse(content={"session_id": sid})


@session_router.post("/{sid}/switch")
async def switch_session(sid: str):
    """切换当前活跃会话（有副作用，使用 POST）"""
    b = _brain()
    err = _check_sid(b, sid)
    if err:
        return err
    if sid == b.session_mgr.current_id:
        return JSONResponse(content={"session_id": sid, "messages": b.history})
    b.session_mgr.save_messages(b.history)
    b.history = b.session_mgr.load(sid)
    b.latest_screenshot = None
    log.info(f"切换会话: {sid}")
    return JSONResponse(content={"session_id": sid, "messages": b.history})


@session_router.put("/{sid}")
async def rename_session(sid: str, request: Request):
    b = _brain()
    err = _check_sid(b, sid)
    if err:
        return err
    data = await request.json()
    if not isinstance(data, dict):
        data = {}
    title = data.get("title", "").strip()
    if not title:
        return JSONResponse(content={"error": "标题不能为空"}, status_code=400)
    title = title[:100]
    b.session_mgr.rename(sid, title)
    log.info(f"重命名会话: {sid}")
    return JSONResponse(content={"status": "ok"})


@session_router.delete("/{sid}")
async def delete_session(sid: str):
    b = _brain()
    err = _check_sid(b, sid)
    if err:
        return err
    was_current = sid == b.session_mgr.current_id
    b.session_mgr.delete(sid)
    log.info(f"删除会话: {sid}")
    if was_current:
        if b.session_mgr.current_id:
            b.history = b.session_mgr.load(b.session_mgr.current_id)
        else:
            b.session_mgr.create()
            b.history = []
        b.latest_screenshot = None
    return JSONResponse(content={
        "status": "ok",
        "current_id": b.session_mgr.current_id,
        "messages": b.history if was_current else None,
    })
