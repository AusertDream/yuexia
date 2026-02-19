"""Faster-Whisper + Silero-VAD 语音识别（双模式）"""
import asyncio
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from src.core.config import get
from src.core.logger import get_logger

log = get_logger("asr")

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.5


class ASREngine:
    def __init__(self):
        self.model = None
        self.vad_model = None
        self._running = False
        self._mode = get("perception.asr.mic_mode", "always_on")
        self._device_index = get("perception.asr.mic_device", None)
        self._ptt_recording = False
        self._ptt_buffer = []
        self._ptt_lock = threading.Lock()

    def _load(self):
        from faster_whisper import WhisperModel
        import torch

        model_path = get("perception.asr.model_path", "base")
        device = get("perception.asr.device", "cuda")
        compute_type = get("perception.asr.compute_type", "float16")
        self.model = WhisperModel(model_path, device=device, compute_type=compute_type)

        self.vad_model, vad_utils = torch.hub.load(
            "snakers4/silero-vad", "silero_vad", trust_repo=True
        )
        self.get_speech_timestamps = vad_utils[0]
        self.vad_threshold = get("perception.asr.vad_threshold", 0.5)
        log.info("ASR 引擎已加载")

    def set_mode(self, mode: str):
        self._mode = mode
        log.info(f"麦克风模式切换: {mode}")

    def set_device(self, index):
        self._device_index = index
        log.info(f"麦克风设备切换: {index}")

    @staticmethod
    def list_devices() -> list[dict]:
        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(devices) if d["max_input_channels"] > 0
        ]

    def mic_test(self, duration: float = 3.0) -> str:
        """录制指定时长，保存为 wav 返回路径"""
        log.info(f"麦克风测试录音 {duration}s")
        audio = sd.rec(
            int(SAMPLE_RATE * duration), samplerate=SAMPLE_RATE,
            channels=1, device=self._device_index, dtype="float32",
        )
        sd.wait()
        out = Path("data/mic_test.wav")
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out), audio, SAMPLE_RATE)
        log.info(f"麦克风测试录音保存: {out}")
        return str(out)

    def start_ptt(self):
        with self._ptt_lock:
            self._ptt_buffer.clear()
            self._ptt_recording = True
        log.info("PTT 开始录音")

    def stop_ptt(self):
        with self._ptt_lock:
            self._ptt_recording = False
        log.info("PTT 停止录音")

    async def start_listening(self, callback):
        try:
            self._load()
        except Exception as e:
            log.error(f"ASR 引擎加载失败: {e}", exc_info=True)
            return
        self._running = True
        loop = asyncio.get_event_loop()
        buffer = []
        lock = threading.Lock()

        def audio_callback(indata, frames, time_info, status):
            if not self._running:
                return
            data = indata[:, 0].copy()
            with lock:
                buffer.append(data)
            if self._ptt_recording:
                with self._ptt_lock:
                    self._ptt_buffer.append(data)

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1,
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
            callback=audio_callback, device=self._device_index,
        )
        stream.start()
        log.info("麦克风监听已启动")

        silence_count = 0
        speech_buffer = []

        while self._running:
            await asyncio.sleep(CHUNK_DURATION)

            # PTT：无论什么模式，录音结束且有数据就转录
            ptt_audio = None
            if not self._ptt_recording:
                with self._ptt_lock:
                    if self._ptt_buffer:
                        ptt_audio = np.concatenate(self._ptt_buffer)
                        self._ptt_buffer.clear()
            if ptt_audio is not None:
                text = await loop.run_in_executor(None, self._transcribe, ptt_audio)
                if text.strip():
                    await callback(text)
                continue

            # always_on 模式: VAD 检测
            if self._mode != "always_on":
                continue
            with lock:
                if not buffer:
                    continue
                chunk = np.concatenate(buffer)
                buffer.clear()

            is_speech = await loop.run_in_executor(None, self._detect_speech, chunk)
            if is_speech:
                speech_buffer.append(chunk)
                silence_count = 0
            elif speech_buffer:
                silence_count += 1
                if silence_count >= 3:
                    audio = np.concatenate(speech_buffer)
                    speech_buffer.clear()
                    silence_count = 0
                    text = await loop.run_in_executor(None, self._transcribe, audio)
                    if text.strip():
                        await callback(text)

        stream.stop()
        stream.close()

    def _detect_speech(self, audio: np.ndarray) -> bool:
        import torch
        # Silero VAD 要求 16kHz 时每次恰好 512 采样点
        window = 512
        for i in range(0, len(audio) - window + 1, window):
            chunk = torch.FloatTensor(audio[i:i + window])
            if self.vad_model(chunk, SAMPLE_RATE).item() > self.vad_threshold:
                return True
        return False

    def _transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(audio, language="zh")
        return "".join(seg.text for seg in segments)

    def stop(self):
        self._running = False
