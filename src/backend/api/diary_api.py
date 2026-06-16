"""日记查看 API：只读，列出与读取 data/diary/ 下的日记条目"""
import re
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger

log = get_logger("api.diary")

diary_router = APIRouter(prefix="/api/diary")

# 文件名前缀 → 日记类型
_PREFIX_TO_TYPE = {"日记": "daily", "周记": "weekly", "月记": "monthly", "年记": "yearly"}
# 文件名解析：可选「类型前缀_」+ 日期(YYYY-MM-DD) + _ + 时间(HHMMSS)
_NAME_RE = re.compile(r"^(?:(日记|周记|月记|年记)_)?(\d{4}-\d{2}-\d{2})_(\d{6})$")

_PREVIEW_LEN = 80


def _diary_dir():
    return resolve_path(get("diary.output_dir", "data/diary"))


def _parse_meta(filename: str):
    """从文件名解析类型、日期、时间。无法解析则返回 None。"""
    stem = filename[:-3] if filename.endswith(".md") else filename
    m = _NAME_RE.match(stem)
    if not m:
        return None
    prefix, date, hms = m.group(1), m.group(2), m.group(3)
    diary_type = _PREFIX_TO_TYPE.get(prefix, "daily")
    time_str = f"{hms[0:2]}:{hms[2:4]}:{hms[4:6]}"
    return {"type": diary_type, "date": date, "time": time_str, "sort_key": f"{date}_{hms}"}


def _extract_title_preview(text: str):
    """取首个 # 标题作为标题，去掉标题后的正文前若干字符作为预览。"""
    title = ""
    body_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not title and stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            continue
        if stripped:
            body_lines.append(stripped)
    preview = " ".join(body_lines)
    if len(preview) > _PREVIEW_LEN:
        preview = preview[:_PREVIEW_LEN] + "…"
    return title, preview


@diary_router.get("")
async def list_diary():
    """列出所有日记条目，按时间倒序。"""
    d = _diary_dir()
    if not d.exists():
        return JSONResponse(content={"entries": []})
    entries = []
    for f in d.glob("*.md"):
        meta = _parse_meta(f.name)
        if meta is None:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            log.debug(f"日记读取失败: {f.name}", exc_info=True)
            text = ""
        title, preview = _extract_title_preview(text)
        entries.append({
            "name": f.name,
            "type": meta["type"],
            "date": meta["date"],
            "time": meta["time"],
            "title": title,
            "preview": preview,
            "_sort": meta["sort_key"],
        })
    entries.sort(key=lambda e: e["_sort"], reverse=True)
    for e in entries:
        del e["_sort"]
    return JSONResponse(content={"entries": entries})


@diary_router.get("/{name}")
async def read_diary(name: str):
    """读取单篇日记全文。文件名做路径遍历防护。"""
    # 路径遍历防护：拒绝分隔符与上级引用
    if "/" in name or "\\" in name or ".." in name:
        return JSONResponse(content={"error": "非法文件名"}, status_code=400)
    if not name.endswith(".md"):
        return JSONResponse(content={"error": "非法文件名"}, status_code=400)
    d = _diary_dir()
    target = (d / name).resolve()
    # 解析后必须仍在日记目录内
    try:
        target.relative_to(d.resolve())
    except ValueError:
        return JSONResponse(content={"error": "非法文件名"}, status_code=400)
    if not target.is_file():
        return JSONResponse(content={"error": "日记不存在"}, status_code=404)
    meta = _parse_meta(name)
    try:
        content = target.read_text(encoding="utf-8")
    except Exception:
        log.exception(f"日记读取失败: {name}")
        return JSONResponse(content={"error": "读取失败"}, status_code=500)
    return JSONResponse(content={
        "name": name,
        "type": meta["type"] if meta else "daily",
        "date": meta["date"] if meta else "",
        "time": meta["time"] if meta else "",
        "content": content,
    })
