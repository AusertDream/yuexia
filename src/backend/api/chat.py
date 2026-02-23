"""聊天 SSE 流式端点"""
import json
from flask import Blueprint, request, Response, jsonify

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
MAX_INPUT_LENGTH = 4096


@chat_bp.route("/stream", methods=["POST"])
def stream_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "请求体必须是 JSON 对象"}), 400
    text = data.get("text", "")
    if not text or not text.strip():
        return jsonify({"error": "消息内容不能为空"}), 400
    if len(text) > MAX_INPUT_LENGTH:
        return jsonify({"error": f"消息长度不能超过 {MAX_INPUT_LENGTH} 字符"}), 400
    from src.backend.services import get_brain
    brain = get_brain()
    if brain is None:
        return jsonify({"error": "AI 引擎正在加载中，请稍后再试"}), 503

    def generate():
        for item in brain.chat_stream(text.strip()):
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
