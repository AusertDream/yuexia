"""聊天 SSE 流式端点"""
import json
from flask import Blueprint, request, Response, jsonify
from src.backend.core.logger import get_logger

log = get_logger("api.chat")

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
MAX_INPUT_LENGTH = 4096


@chat_bp.route("/stream", methods=["POST"])
def stream_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "请求体必须是 JSON 对象"}), 400
    text = data.get("text", "")
    if not text or not text.strip():
        log.warning("拒绝空消息请求")
        return jsonify({"error": "消息内容不能为空"}), 400
    if len(text) > MAX_INPUT_LENGTH:
        log.warning(f"拒绝超长消息, 长度={len(text)}")
        return jsonify({"error": f"消息长度不能超过 {MAX_INPUT_LENGTH} 字符"}), 400
    from src.backend.services import get_brain
    brain = get_brain()
    if brain is None:
        log.warning("引擎未就绪，拒绝请求")
        return jsonify({"error": "AI 引擎正在加载中，请稍后再试"}), 503
    log.info(f"收到聊天请求, 长度={len(text)}")

    def generate():
        try:
            for item in brain.chat_stream(text.strip()):
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except GeneratorExit:
            log.info("SSE 客户端断开连接")
        except Exception as e:
            log.exception("SSE 流异常")
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
