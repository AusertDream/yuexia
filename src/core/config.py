"""全局配置加载"""
from pathlib import Path
from typing import Any
import yaml

_config: dict | None = None
_config_path: str = "config.yaml"

def load_config(path: str | Path = "config.yaml") -> dict:
    global _config, _config_path
    _config_path = str(path)
    with open(path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config

def reload_config() -> dict:
    global _config
    with open(_config_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    return _config

def get_config() -> dict:
    if _config is None:
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
