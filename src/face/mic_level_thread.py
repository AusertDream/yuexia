"""麦克风音量检测线程"""
from __future__ import annotations
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal


class MicLevelThread(QThread):
    """实时采集麦克风音量，emit 0~100 的 level 值"""
    level_changed = Signal(int)

    def __init__(self, device=None, parent=None):
        super().__init__(parent)
        self._device = device
        self._running = False

    def run(self):
        self._running = True
        try:
            with sd.InputStream(
                device=self._device, channels=1, samplerate=16000,
                blocksize=1024, dtype="float32",
                callback=self._audio_cb,
            ):
                while self._running:
                    self.msleep(50)
        except Exception:
            pass

    def _audio_cb(self, indata, frames, time, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        level = min(100, int(rms * 500))
        self.level_changed.emit(level)

    def stop(self):
        self._running = False
        self.wait(2000)
