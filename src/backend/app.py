"""Flask 应用工厂 + 入口"""
import os
import logging

_env_root = os.environ.get("YUEXIA_ROOT", "").strip()
ROOT_DIR = _env_root if _env_root else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)
socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("YUEXIA_SECRET_KEY", "yuexia-dev")
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # TTS 音频静态文件路由
    tts_dir = os.path.join(ROOT_DIR, "data", "tts_output")
    os.makedirs(tts_dir, exist_ok=True)

    @app.route("/audio/<path:filename>")
    def serve_audio(filename):
        from flask import send_from_directory
        return send_from_directory(tts_dir, filename)

    # 加载配置
    config_path = os.path.join(ROOT_DIR, "config", "config.yaml")
    from src.backend.core.config import load_config
    load_config(config_path)

    # 注册 blueprints
    from src.backend.api import register_blueprints
    register_blueprints(app)

    # 初始化 SocketIO
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    # 注册 WebSocket 命名空间（需在 socketio.init_app 之后）
    from src.backend.api.ws import register_ws
    register_ws(socketio)

    # 全局异常处理
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return jsonify({"error": e.name, "detail": e.description}), e.code
        log.exception("服务器内部错误")
        return jsonify({"error": "服务器内部错误", "detail": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()

    from src.backend.core.config import get
    port = get("server.backend_port", 5000)

    # 写入运行时端口文件
    runtime_dir = os.path.join(ROOT_DIR, ".runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    with open(os.path.join(runtime_dir, "backend_port"), "w") as f:
        f.write(str(port))

    # 后台线程加载服务（不阻塞 Flask 启动）
    from src.backend.services import boot_services
    socketio.start_background_task(boot_services, socketio)

    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
