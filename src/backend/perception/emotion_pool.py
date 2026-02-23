"""情感参考音频池管理"""
from pathlib import Path
import random
import yaml
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("emotion_pool")


class EmotionPool:
    """按情感目录扫描参考音频，支持 meta.yaml 配置"""

    def __init__(self):
        self.refs_dir = Path(get("perception.tts.emotion_refs_dir", "assets/emotion_refs"))
        self.pool: dict[str, list[dict]] = {}
        self._scan()

    def _scan(self):
        if not self.refs_dir.exists():
            log.warning(f"情感音频目录不存在: {self.refs_dir}")
            return
        for emo_dir in self.refs_dir.iterdir():
            if not emo_dir.is_dir():
                continue
            emotion = emo_dir.name
            meta_path = emo_dir / "meta.yaml"
            entries = []
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    entries = yaml.safe_load(f) or []
            else:
                for audio in emo_dir.glob("*.wav"):
                    txt_file = audio.with_name(audio.stem + "Text.txt")
                    text = txt_file.read_text("utf-8").strip() if txt_file.exists() else ""
                    entries.append({"path": str(audio.resolve()), "text": text})
            self.pool[emotion] = entries
        log.info(f"情感音频池已加载: {list(self.pool.keys())}")

    def get_ref(self, emotion: str) -> dict | None:
        """返回 {path, text}，无匹配则回退 neutral"""
        entries = self.pool.get(emotion) or self.pool.get("neutral") or self.pool.get("default", [])
        return random.choice(entries) if entries else None
