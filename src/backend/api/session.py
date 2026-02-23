"""会话管理 API"""
from flask import Blueprint, request, jsonify
from src.backend.core.logger import get_logger

log = get_logger("api.session")

session_bp = Blueprint("session", __name__, url_prefix="/api/sessions")


def _brain():
    from src.backend.services import get_brain
    b = get_brain()
    if b is None:
        from flask import abort
        abort(503, description="服务未就绪")
    return b


def _check_sid(brain, sid):
    if not any(e["id"] == sid for e in brain.session_mgr.index):
        return jsonify({"error": "会话不存在"}), 404
    return None


@session_bp.route("", methods=["GET"])
def list_sessions():
    b = _brain()
    return jsonify({
        "sessions": b.session_mgr.list_sessions(),
        "current_id": b.session_mgr.current_id,
    })


@session_bp.route("", methods=["POST"])
def create_session():
    b = _brain()
    b.session_mgr.save_messages(b.history)
    sid = b.session_mgr.create()
    b.history = []
    b.latest_screenshot = None
    log.info(f"创建会话: {sid}")
    return jsonify({"session_id": sid})


@session_bp.route("/<sid>", methods=["GET"])
def switch_session(sid):
    b = _brain()
    err = _check_sid(b, sid)
    if err:
        return err
    if sid == b.session_mgr.current_id:
        return jsonify({"session_id": sid, "messages": b.history})
    b.session_mgr.save_messages(b.history)
    b.history = b.session_mgr.load(sid)
    b.latest_screenshot = None
    log.info(f"切换会话: {sid}")
    return jsonify({"session_id": sid, "messages": b.history})


@session_bp.route("/<sid>", methods=["PUT"])
def rename_session(sid):
    b = _brain()
    err = _check_sid(b, sid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "标题不能为空"}), 400
    title = title[:100]
    b.session_mgr.rename(sid, title)
    log.info(f"重命名会话: {sid}")
    return jsonify({"status": "ok"})


@session_bp.route("/<sid>", methods=["DELETE"])
def delete_session(sid):
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
    return jsonify({
        "status": "ok",
        "current_id": b.session_mgr.current_id,
        "messages": b.history if was_current else None,
    })
