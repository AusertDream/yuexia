"""配置 API"""
import copy
import os
import yaml
from flask import Blueprint, request, jsonify
from src.backend.core.logger import get_logger

log = get_logger("api.config")

config_bp = Blueprint("config", __name__, url_prefix="/api")

# 允许用户修改的配置项白名单
CONFIG_WHITELIST = frozenset({
    "general.dark_mode",
    "general.accent_color",
    "brain.engine",
    "brain.model_path",
    "brain.system_prompt",
    "brain.temperature",
    "brain.max_tokens",
    "brain.top_p",
    "brain.gpu_memory_utilization",
    "brain.enable_thinking",
    "brain.context_length",
    "brain.stream",
    "perception.tts.api_url",
    "perception.tts.sovits_weights",
    "perception.tts.gpt_weights",
    "perception.tts.output_device",
    "perception.asr.model_size",
    "perception.asr.compute_type",
    "perception.asr.vad_threshold",
    "perception.asr.mic_device",
    "memory.enabled",
    "memory.collection_name",
    "memory.embedding_model",
    "memory.auto_persist",
    "action.screen.enabled",
    "action.screen.interval",
})


def _flatten_keys(d: dict, prefix: str = "") -> set[str]:
    """将嵌套 dict 展平为点分路径集合，如 {"brain": {"max_tokens": 100}} -> {"brain.max_tokens"}"""
    keys = set()
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(_flatten_keys(v, full_key))
        else:
            keys.add(full_key)
    return keys

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "config.yaml")
EMOTION_REFS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "emotion_refs")


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


@config_bp.route("/config", methods=["GET"])
def get_config():
    from src.backend.core.config import get_config
    return jsonify(get_config())


@config_bp.route("/config", methods=["PUT"])
def update_config():
    new_config = request.get_json(silent=True)
    if not isinstance(new_config, dict):
        return jsonify({"error": "请求体必须是 JSON 对象"}), 400

    # 白名单检查：只允许修改指定的配置项
    requested_keys = _flatten_keys(new_config)
    forbidden_keys = requested_keys - CONFIG_WHITELIST
    if forbidden_keys:
        log.warning(f"拒绝修改非白名单配置项: {forbidden_keys}")
        return jsonify({
            "error": "禁止修改的配置项",
            "forbidden_keys": list(forbidden_keys),
            "allowed_keys": list(CONFIG_WHITELIST)
        }), 403

    existing = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}
    merged = _deep_merge(existing, new_config)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(merged, f, allow_unicode=True, default_flow_style=False)
    from src.backend.core.config import reload_config
    reload_config()
    from src.backend.services import reload_services
    reload_services()
    log.info("配置已更新")
    return jsonify({"status": "ok"})


@config_bp.route("/emotion-refs", methods=["GET"])
def get_emotion_refs():
    refs = []
    if os.path.isdir(EMOTION_REFS_DIR):
        for f in sorted(os.listdir(EMOTION_REFS_DIR)):
            if f.endswith((".wav", ".mp3", ".ogg")):
                name = os.path.splitext(f)[0]
                emotion = name.split("_")[0] if "_" in name else name
                refs.append({"emotion": emotion, "file": f})
    return jsonify(refs)
