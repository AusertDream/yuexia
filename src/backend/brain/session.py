"""会话持久化管理"""
import json
import re
import secrets
import threading
import time
from pathlib import Path
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger

log = get_logger("session")

_VALID_SID_RE = re.compile(r'^[0-9a-f]+$')


class SessionManager:
    def __init__(self):
        self.dir = resolve_path(get("session.dir", "data/sessions"))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.dir / "index.json"
        self.current_id: str | None = None
        self._lock = threading.RLock()  # 并发保护锁
        self.index: list[dict] = self._load_index()

    @staticmethod
    def _validate_session_id(sid: str) -> bool:
        """校验 session_id 只允许十六进制字符，防止路径遍历"""
        return bool(sid) and bool(_VALID_SID_RE.match(sid))

    def _atomic_write(self, path: Path, content: str):
        """原子写入：先写临时文件，成功后替换原文件（Windows 兼容）"""
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(content, "utf-8")
        try:
            tmp_path.replace(path)
        except PermissionError:
            log.warning(f"原子替换失败（文件可能被锁定），回退到直接写入: {path}")
            path.write_text(content, "utf-8")
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _load_index(self) -> list[dict]:
        with self._lock:
            if self.index_file.exists():
                return json.loads(self.index_file.read_text("utf-8"))
            return []

    def _save_index(self):
        # 调用者必须已持有 self._lock
        self._atomic_write(
            self.index_file,
            json.dumps(self.index, ensure_ascii=False, indent=2)
        )

    def create(self) -> str:
        with self._lock:
            # 使用 secrets.token_hex(16) 生成 32 位十六进制 ID
            sid = secrets.token_hex(16)
            now = time.time()
            data = {"id": sid, "title": "新对话", "created_at": now, "updated_at": now, "messages": []}
            self._atomic_write(
                self.dir / f"{sid}.json",
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            self.index.insert(0, {"id": sid, "title": "新对话", "updated_at": now})
            self._save_index()
            self.current_id = sid
            return sid

    def load(self, sid: str) -> list[dict]:
        if not self._validate_session_id(sid):
            log.warning(f"非法 session_id: {sid!r}")
            return []
        with self._lock:
            path = self.dir / f"{sid}.json"
            if not path.exists():
                return []
            data = json.loads(path.read_text("utf-8"))
            self.current_id = sid
            return data.get("messages", [])

    def save_messages(self, messages: list[dict]):
        with self._lock:
            if not self.current_id:
                return
            path = self.dir / f"{self.current_id}.json"
            if not path.exists():
                return
            data = json.loads(path.read_text("utf-8"))
            data["messages"] = messages
            data["updated_at"] = time.time()
            for m in messages:
                if m["role"] == "user":
                    data["title"] = m["content"][:20]
                    break
            self._atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
            for entry in self.index:
                if entry["id"] == self.current_id:
                    entry["updated_at"] = data["updated_at"]
                    entry["title"] = data["title"]
                    break
            self._save_index()

    def rename(self, sid: str, title: str):
        if not self._validate_session_id(sid):
            log.warning(f"非法 session_id: {sid!r}")
            return
        with self._lock:
            path = self.dir / f"{sid}.json"
            if path.exists():
                data = json.loads(path.read_text("utf-8"))
                data["title"] = title
                self._atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
            for entry in self.index:
                if entry["id"] == sid:
                    entry["title"] = title
                    break
            self._save_index()

    def delete(self, sid: str):
        if not self._validate_session_id(sid):
            log.warning(f"非法 session_id: {sid!r}")
            return
        with self._lock:
            path = self.dir / f"{sid}.json"
            if path.exists():
                try:
                    data = json.loads(path.read_text("utf-8"))
                    for m in data.get("messages", []):
                        tts = m.get("tts_path", "")
                        if tts:
                            p = Path(tts)
                            if p.exists():
                                p.unlink()
                except Exception:
                    log.warning(f"清理会话 {sid} 音频文件时出错", exc_info=True)
                path.unlink()
            self.index = [e for e in self.index if e["id"] != sid]
            self._save_index()
            if self.current_id == sid:
                self.current_id = self.index[0]["id"] if self.index else None

    def list_sessions(self) -> list[dict]:
        with self._lock:
            return sorted(self.index, key=lambda x: x.get("updated_at", 0), reverse=True)
