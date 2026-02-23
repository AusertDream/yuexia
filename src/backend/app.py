"""Flask 应用工厂 + 入口"""
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

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

    return app


if __name__ == "__main__":
    app = create_app()

    # 后台线程加载服务（不阻塞 Flask 启动）
    from src.backend.services import boot_services
    socketio.start_background_task(boot_services, socketio)

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
