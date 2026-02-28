"""情感参考音频池管理"""
from pathlib import Path
import random
import yaml
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger

log = get_logger("emotion_pool")


class EmotionPool:
    """按情感目录扫描参考音频，支持 meta.yaml 配置"""

    def __init__(self):
        self.refs_dir = resolve_path(get("perception.tts.emotion_refs_dir", "assets/emotion_refs"))
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
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        raw = yaml.safe_load(f)
                    # 校验 yaml 格式和必要字段
                    if not isinstance(raw, list):
                        log.warning(f"meta.yaml 格式错误（应为列表）: {meta_path}")
                        raw = []
                    for item in raw:
                        if not isinstance(item, dict):
                            log.warning(f"meta.yaml 条目格式错误（应为字典）: {meta_path}")
                            continue
                        if "path" not in item or "text" not in item:
                            log.warning(f"meta.yaml 条目缺少 path 或 text 字段: {meta_path}")
                            continue
                        entries.append(item)
                except yaml.YAMLError as e:
                    log.warning(f"meta.yaml 解析失败: {meta_path}, 错误: {e}")
                except Exception as e:
                    log.warning(f"读取 meta.yaml 异常: {meta_path}, 错误: {e}")
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
