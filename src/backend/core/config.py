"""全局配置加载"""
import os
from pathlib import Path
from typing import Any
import yaml

_config: dict | None = None
_config_path: str = "config.yaml"

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
    },
    "memory": {
        "enabled": False,
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
    _config_path = str(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    _config = _deep_merge(_DEFAULTS, raw)
    return _config


def reload_config() -> dict:
    global _config
    with open(_config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    _config = _deep_merge(_DEFAULTS, raw)
    return _config


def get_config() -> dict:
    if _config is None:
        root = os.environ.get("YUEXIA_ROOT")
        if root:
            return load_config(os.path.join(root, "config", "config.yaml"))
        return load_config()
    return _config


def get(key: str, default: Any = None) -> Any:
    """点分路径取值，如 'brain.engine'"""
    cfg = get_config()
    for k in key.split("."):
        if isinstance(cfg, dict):
            cfg = cfg.get(k, default)
        else:
            return default
    return cfg
