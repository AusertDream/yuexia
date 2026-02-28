"""配置 API"""
import copy
import os
import yaml
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.backend.core.logger import get_logger

log = get_logger("api.config")

config_router = APIRouter(prefix="/api")

# 允许用户修改的配置项白名单
CONFIG_WHITELIST = frozenset({
    "general.dark_mode",
    "general.accent_color",
    "general.language",
    "general.font_size",
    "general.animation_enabled",
    "general.sidebar_width",
    "general.message_bubble_style",
    "general.notification_enabled",
    "general.notification_sound",
    "brain.engine",
    "brain.api_url",
    "brain.api_key",
    "brain.api_model",
    "brain.model_path",
    "brain.system_prompt_path",
    "brain.temperature",
    "brain.max_tokens",
    "brain.top_p",
    "brain.gpu_memory_utilization",
    "brain.enable_thinking",
    "brain.context_length",
    "brain.stream",
    "brain.repetition_penalty",
    "brain.frequency_penalty",
    "brain.presence_penalty",
    "brain.top_k",
    "brain.min_p",
    "brain.do_sample",
    "brain.stop_sequences",
    "brain.num_beams",
    "perception.tts.api_url",
    "perception.tts.sovits_weights",
    "perception.tts.gpt_weights",
    "perception.tts.output_device",
    "perception.tts.speed",
    "perception.tts.volume",
    "perception.tts.emotion_intensity",
    "perception.tts.timeout",
    "perception.tts.retry_count",
    "perception.tts.retry_delay",
    "perception.tts.output_format",
    "perception.tts.ref_audio_dir",
    "perception.tts.engine",
    "perception.tts.api_key",
    "perception.tts.output_dir",
    "perception.asr.model_size",
    "perception.asr.compute_type",
    "perception.asr.vad_threshold",
    "perception.asr.mic_device",
    "perception.asr.language",
    "perception.asr.beam_size",
    "perception.asr.best_of",
    "perception.asr.patience",
    "perception.asr.initial_prompt",
    "perception.asr.suppress_tokens",
    "memory.enabled",
    "memory.collection_name",
    "memory.embedding_model",
    "memory.auto_persist",
    "memory.retrieval_count",
    "memory.similarity_threshold",
    "memory.auto_persist_interval",
    "memory.max_memories",
    "memory.db_path",
    "action.screen.enabled",
    "action.screen.interval",
    "behavior.enabled",
    "behavior.interval_minutes",
    "behavior.trigger_type",
    "behavior.idle_timeout_minutes",
    "behavior.cron_expression",
    "behavior.message_templates_enabled",
    "behavior.llm_generation_enabled",
    "behavior.max_daily_messages",
    "behavior.quiet_hours_start",
    "behavior.quiet_hours_end",
    "behavior.categories",
    "session.max_history_messages",
    "session.auto_save_interval",
    "session.auto_title_generation",
    "session.max_message_length",
    "session.export_format",
    "session.dir",
    "security.api_access_control",
    "security.allowed_origins",
    "security.log_level",
    "security.max_request_size_mb",
    "security.rate_limit_per_minute",
    "network.proxy_url",
    "network.request_timeout",
    "network.connect_timeout",
    "network.retry_count",
    "network.pool_size",
    "network.pool_max_size",
    "network.proxy_enabled",
    "diary.enabled",
    "diary.auto_generate",
    "diary.generation_time",
    "diary.output_dir",
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


_SENSITIVE_KEYS = {"api_key"}


def _mask_sensitive(d: dict):
    for k, v in d.items():
        if isinstance(v, dict):
            _mask_sensitive(v)
        elif k in _SENSITIVE_KEYS and isinstance(v, str) and v:
            d[k] = v[:3] + "***" if len(v) > 3 else "***"


@config_router.get("/config")
async def get_config():
    from src.backend.core.config import get_config
    cfg = copy.deepcopy(get_config())
    _mask_sensitive(cfg)
    return JSONResponse(content=cfg)


@config_router.put("/config")
async def update_config(request: Request):
    new_config = await request.json()
    if not isinstance(new_config, dict):
        return JSONResponse(content={"error": "请求体必须是 JSON 对象"}, status_code=400)

    # 白名单检查：只允许修改指定的配置项
    requested_keys = _flatten_keys(new_config)
    forbidden_keys = requested_keys - CONFIG_WHITELIST
    if forbidden_keys:
        log.warning(f"拒绝修改非白名单配置项: {forbidden_keys}")
        return JSONResponse(content={
            "error": "禁止修改的配置项",
            "forbidden_keys": list(forbidden_keys),
            "allowed_keys": list(CONFIG_WHITELIST)
        }, status_code=403)

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
    return JSONResponse(content={"status": "ok"})


@config_router.get("/emotion-refs")
async def get_emotion_refs():
    refs = []
    if os.path.isdir(EMOTION_REFS_DIR):
        for f in sorted(os.listdir(EMOTION_REFS_DIR)):
            if f.endswith((".wav", ".mp3", ".ogg")):
                name = os.path.splitext(f)[0]
                emotion = name.split("_")[0] if "_" in name else name
                refs.append({"emotion": emotion, "file": f})
    return JSONResponse(content=refs)
