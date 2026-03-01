"""配置 API"""
import copy
import os
import shutil
import glob as globmod
import yaml
from fastapi import APIRouter, Request, UploadFile, File
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
    # 新增日记类型配置
    "diary.daily.enabled",
    "diary.daily.frequency",
    "diary.daily.prompt",
    "diary.weekly.enabled",
    "diary.weekly.frequency",
    "diary.weekly.prompt",
    "diary.monthly.enabled",
    "diary.monthly.frequency",
    "diary.monthly.prompt",
    "diary.yearly.enabled",
    "diary.yearly.frequency",
    "diary.yearly.prompt",
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

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "config.yaml")
EMOTION_REFS_DIR = os.path.join(ROOT_DIR, "assets", "emotion_refs")


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


def _filter_whitelisted(d: dict, prefix: str = "") -> dict:
    """递归过滤，只保留白名单中的配置项"""
    result = {}
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            filtered = _filter_whitelisted(v, full_key)
            if filtered:
                result[k] = filtered
        elif full_key in CONFIG_WHITELIST:
            result[k] = v
    return result


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

    # 白名单过滤：只保留允许修改的配置项，忽略其余
    requested_keys = _flatten_keys(new_config)
    forbidden_keys = requested_keys - CONFIG_WHITELIST
    if forbidden_keys:
        log.debug(f"过滤非白名单配置项: {forbidden_keys}")
        new_config = _filter_whitelisted(new_config)

    if not new_config:
        return JSONResponse(content={"status": "ok", "message": "无可更新的配置项"})

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


@config_router.get("/config/chat-bg")
async def get_chat_bg():
    """查询当前聊天背景图片"""
    photos_dir = os.path.join(ROOT_DIR, "data", "photos")
    for ext in ("png", "jpg", "jpeg", "webp", "gif"):
        matches = globmod.glob(os.path.join(photos_dir, f"chat-bg.{ext}"))
        if matches:
            filename = os.path.basename(matches[0])
            return {"exists": True, "url": f"/photos/{filename}"}
    return {"exists": False, "url": None}


@config_router.post("/config/chat-bg")
async def upload_chat_bg(file: UploadFile = File(...)):
    """上传聊天背景图片"""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse({"error": "只允许上传图片文件"}, status_code=400)
    photos_dir = os.path.join(ROOT_DIR, "data", "photos")
    os.makedirs(photos_dir, exist_ok=True)
    # 清除旧背景
    for old in globmod.glob(os.path.join(photos_dir, "chat-bg.*")):
        os.remove(old)
    # 保存新背景
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    dest = os.path.join(photos_dir, f"chat-bg.{ext}")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    log.info("聊天背景已更新: %s", dest)
    return {"exists": True, "url": f"/photos/chat-bg.{ext}"}


@config_router.delete("/config/chat-bg")
async def delete_chat_bg():
    """删除聊天背景图片，恢复默认"""
    photos_dir = os.path.join(ROOT_DIR, "data", "photos")
    deleted = False
    for old in globmod.glob(os.path.join(photos_dir, "chat-bg.*")):
        os.remove(old)
        deleted = True
    if deleted:
        log.info("聊天背景已清除")
    return {"exists": False, "url": None}


@config_router.post("/diary/immediate")
async def trigger_immediate_diary():
    """触发立即记录日记"""
    from src.backend.services import get_brain
    from src.backend.brain.diary import DiaryWriter
    from src.backend.core.config import get

    brain = get_brain()
    if not brain or not brain.history:
        return JSONResponse(
            content={"error": "没有可用的对话历史"},
            status_code=400
        )

    diary_writer = DiaryWriter()
    results = {}

    # 遍历所有日记类型，生成启用的日记
    for diary_type in ["daily", "weekly", "monthly", "yearly"]:
        enabled = get(f"diary.{diary_type}.enabled", False)
        if enabled:
            try:
                content = await diary_writer.write(
                    brain.history,
                    brain.engine,
                    diary_type
                )
                results[diary_type] = {"status": "success", "content": content}
            except Exception as e:
                log.error(f"生成 {diary_type} 日记失败: {e}", exc_info=True)
                results[diary_type] = {"status": "error", "error": str(e)}

    return JSONResponse(content={"results": results})
