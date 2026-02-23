"""注册所有 API blueprints"""


def register_blueprints(app):
    from src.backend.api.chat import chat_bp
    from src.backend.api.config_api import config_bp
    from src.backend.api.session import session_bp
    from src.backend.api.system import system_bp
    from src.backend.api.asr_api import asr_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(asr_bp)
