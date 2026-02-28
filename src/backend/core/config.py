"""全局配置加载"""
import os
import threading
from pathlib import Path
from typing import Any
import yaml

_config: dict | None = None
_config_path: str = "config.yaml"
_config_lock = threading.RLock()

_DEFAULTS: dict = {
    "server": {
        "backend_port": 5000,
        "frontend_port": 5173,
        "tts_port": 9880,
    },
    "brain": {
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 0.9,
        "engine": "vllm",
        "context_length": 8192,
        "max_model_len": 8192,
        "gpu_memory_utilization": 0.85,
        "enable_thinking": False,
        "stream": True,
        "repetition_penalty": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "top_k": 50,
        "min_p": 0.0,
        "do_sample": True,
        "stop_sequences": [],
        "num_beams": 1,
    },
    "behavior": {
        "enabled": False,
        "interval_minutes": 30,
        "trigger_type": "interval",
        "idle_timeout_minutes": 10,
        "cron_expression": "",
        "message_templates_enabled": True,
        "llm_generation_enabled": False,
        "max_daily_messages": 50,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "07:00",
        "categories": ["问候", "关心", "分享", "思念"],
    },
    "perception": {
        "tts": {
            "speed": 1.0,
            "volume": 1.0,
            "emotion_intensity": 1.0,
            "timeout": 30,
            "retry_count": 2,
            "retry_delay": 1.0,
            "output_format": "wav",
            "ref_audio_dir": "assets/emotion_refs",
            "engine": "local",
            "api_key": "",
        },
        "asr": {
            "language": "zh",
            "beam_size": 5,
            "best_of": 5,
            "patience": 1.0,
            "initial_prompt": "",
            "suppress_tokens": [],
        },
    },
    "general": {
        "dark_mode": True,
        "accent_color": "#60cdff",
        "language": "zh-CN",
        "font_size": 14,
        "animation_enabled": True,
        "sidebar_width": 280,
        "message_bubble_style": "modern",
        "notification_enabled": True,
        "notification_sound": True,
    },
    "session": {
        "max_history_messages": 40,
        "auto_save_interval": 30,
        "auto_title_generation": True,
        "max_message_length": 10000,
        "export_format": "json",
    },
    "memory": {
        "enabled": False,
        "retrieval_count": 5,
        "similarity_threshold": 0.7,
        "auto_persist_interval": 300,
        "max_memories": 10000,
    },
    "security": {
        "api_access_control": False,
        "allowed_origins": ["http://localhost:5173"],
        "log_level": "INFO",
        "max_request_size_mb": 10,
        "rate_limit_per_minute": 60,
    },
    "network": {
        "proxy_url": "",
        "request_timeout": 30,
        "connect_timeout": 10,
        "retry_count": 3,
        "pool_size": 10,
        "pool_max_size": 20,
        "proxy_enabled": False,
    },
    "diary": {
        "enabled": True,
        "auto_generate": False,
        "generation_time": "23:00",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并字典，override 优先"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(path: str | Path = "config.yaml") -> dict:
    global _config, _config_path
    with _config_lock:
        _config_path = str(path)
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        _config = _deep_merge(_DEFAULTS, raw)
        return _config


def reload_config() -> dict:
    global _config
    with _config_lock:
        with open(_config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        _config = _deep_merge(_DEFAULTS, raw)
        return _config


def get_config() -> dict:
    with _config_lock:
        if _config is None:
            root = os.environ.get("YUEXIA_ROOT")
            if root:
                return load_config(os.path.join(root, "config", "config.yaml"))
            return load_config()
        return _config


_SENTINEL = object()


def get(key: str, default: Any = None) -> Any:
    """点分路径取值，如 'brain.engine'"""
    cfg = get_config()
    for k in key.split("."):
        if isinstance(cfg, dict):
            cfg = cfg.get(k, _SENTINEL)
            if cfg is _SENTINEL:
                return default
        else:
            return default
    return cfg


def get_root_dir() -> Path:
    """获取项目根目录：优先使用 YUEXIA_ROOT 环境变量，否则回退到 config.yaml 所在目录"""
    root = os.environ.get("YUEXIA_ROOT")
    if root:
        return Path(root)
    # config.yaml 通常在项目根目录或 config/ 子目录下
    cfg_path = Path(_config_path).resolve()
    if cfg_path.parent.name == "config":
        return cfg_path.parent.parent
    return cfg_path.parent


def resolve_path(relative: str) -> Path:
    """将相对路径解析为基于项目根目录的绝对路径，已是绝对路径则原样返回"""
    p = Path(relative)
    if p.is_absolute():
        return p
    return get_root_dir() / p
