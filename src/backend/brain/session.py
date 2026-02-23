"""会话持久化管理"""
import json
import uuid
import time
from pathlib import Path
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("session")


class SessionManager:
    def __init__(self):
        self.dir = Path(get("session.dir", "data/sessions"))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.dir / "index.json"
        self.current_id: str | None = None
        self.index: list[dict] = self._load_index()

    def _load_index(self) -> list[dict]:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text("utf-8"))
        return []

    def _save_index(self):
        self.index_file.write_text(
            json.dumps(self.index, ensure_ascii=False, indent=2), "utf-8"
        )

    def create(self) -> str:
        sid = uuid.uuid4().hex[:8]
        now = time.time()
        data = {"id": sid, "title": "新对话", "created_at": now, "updated_at": now, "messages": []}
        (self.dir / f"{sid}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), "utf-8"
        )
        self.index.insert(0, {"id": sid, "title": "新对话", "updated_at": now})
        self._save_index()
        self.current_id = sid
        return sid

    def load(self, sid: str) -> list[dict]:
        path = self.dir / f"{sid}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text("utf-8"))
        self.current_id = sid
        return data.get("messages", [])

    def save_messages(self, messages: list[dict]):
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
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        for entry in self.index:
            if entry["id"] == self.current_id:
                entry["updated_at"] = data["updated_at"]
                entry["title"] = data["title"]
                break
        self._save_index()

    def rename(self, sid: str, title: str):
        path = self.dir / f"{sid}.json"
        if path.exists():
            data = json.loads(path.read_text("utf-8"))
            data["title"] = title
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        for entry in self.index:
            if entry["id"] == sid:
                entry["title"] = title
                break
        self._save_index()

    def delete(self, sid: str):
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
        return sorted(self.index, key=lambda x: x.get("updated_at", 0), reverse=True)
