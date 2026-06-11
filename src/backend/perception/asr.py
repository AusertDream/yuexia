"""Faster-Whisper + Silero-VAD ASR 集成"""
import threading
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Generator, Callable
from src.backend.core.config import get, resolve_path
from src.backend.core.logger import get_logger

log = get_logger("asr")


class ASRError(Exception):
    """ASR 识别失败时抛出的异常"""
    pass


class AudioBuffer:
    """音频片段缓冲管理器，用于VAD触发和句子完整性保护"""

    def __init__(self, sample_rate: int = 16000, vad_threshold: float = 0.2):
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self.buffer = []
        self.silence_duration = 0.0
        self.max_silence = 1.5  # 静音超过1.5秒触发识别
        self._lock = threading.Lock()

    def add_chunk(self, audio_chunk: np.ndarray, is_speech: bool) -> bool:
        """
        添加音频片段到缓冲区

        Args:
            audio_chunk: 音频数据（numpy数组）
            is_speech: VAD检测结果，True表示有语音

        Returns:
            bool: 是否应该触发识别（检测到足够长的静音）
        """
        with self._lock:
            self.buffer.append(audio_chunk)

            if is_speech:
                self.silence_duration = 0.0
                return False
            else:
                # 累积静音时长
                chunk_duration = len(audio_chunk) / self.sample_rate
                self.silence_duration += chunk_duration

                # 静音超过阈值且缓冲区有内容，触发识别
                if self.silence_duration >= self.max_silence and len(self.buffer) > 0:
                    return True

            return False

    def get_audio(self) -> Optional[np.ndarray]:
        """获取缓冲区中的完整音频并清空缓冲"""
        with self._lock:
            if not self.buffer:
                return None

            audio = np.concatenate(self.buffer)
            self.buffer = []
            self.silence_duration = 0.0
            return audio

    def clear(self):
        """清空缓冲区"""
        with self._lock:
            self.buffer = []
            self.silence_duration = 0.0


class ASREngine:
    """Faster-Whisper ASR 引擎，支持文件转写和实时识别"""

    def __init__(self):
        self._model = None
        self._vad_model = None
        self._lock = threading.Lock()
        self._loading = False
        self._device = get("perception.asr.device", "cuda")
        self._compute_type = get("perception.asr.compute_type", "int8")
        self._model_size = get("perception.asr.model_size", "medium")
        self._model_path = get("perception.asr.model_path", "")
        self._language = get("perception.asr.language", "zh")
        self._beam_size = get("perception.asr.beam_size", 5)
        self._best_of = get("perception.asr.best_of", 5)
        self._patience = get("perception.asr.patience", 1.0)
        self._initial_prompt = get("perception.asr.initial_prompt", "")
        self._suppress_tokens = get("perception.asr.suppress_tokens", [])
        self._vad_threshold = get("perception.asr.vad_threshold", 0.2)

        # 实时识别相关
        self._realtime_thread = None
        self._realtime_stop_event = threading.Event()
        self._audio_buffer = None
        self._realtime_lock = threading.Lock()

        log.info(f"ASR引擎初始化: device={self._device}, compute_type={self._compute_type}, "
                f"model_size={self._model_size}, language={self._language}")

    def _ensure_model(self):
        """延迟加载模型（首次调用时加载）"""
        if self._model is not None:
            return

        with self._lock:
            # Double-check locking
            if self._model is not None:
                return

            if self._loading:
                log.warning("模型正在加载中，请稍候")
                return

            self._loading = True
            try:
                log.info("开始加载 Faster-Whisper 模型...")

                # 检查是否使用本地模型路径
                if self._model_path and Path(self._model_path).exists():
                    model_path = self._model_path
                    log.info(f"使用本地模型: {model_path}")
                else:
                    model_path = self._model_size
                    log.info(f"使用预训练模型: {model_path}")

                # 导入faster_whisper（延迟导入，避免启动时阻塞）
                try:
                    from faster_whisper import WhisperModel
                except ImportError as e:
                    log.error("faster-whisper 未安装，请运行: pip install faster-whisper")
                    raise ASRError("faster-whisper 未安装") from e

                # 加载模型
                self._model = WhisperModel(
                    model_path,
                    device=self._device,
                    compute_type=self._compute_type,
                    download_root=None  # 使用默认缓存目录
                )

                log.info(f"Faster-Whisper 模型加载成功: {model_path}")

            except Exception as e:
                log.error(f"模型加载失败: {e}", exc_info=True)
                self._model = None
                raise ASRError(f"模型加载失败: {e}") from e
            finally:
                self._loading = False

    def _load_vad(self):
        """加载 Silero-VAD 模型"""
        if self._vad_model is not None:
            return

        with self._lock:
            # Double-check locking
            if self._vad_model is not None:
                return

            try:
                log.info("加载 Silero-VAD 模型...")
                # 使用 torch.hub 加载 silero-vad
                self._vad_model, utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
                self._vad_model.eval()
                log.info("Silero-VAD 模型加载成功")
            except Exception as e:
                log.error(f"VAD 模型加载失败: {e}", exc_info=True)
                self._vad_model = None
                raise ASRError(f"VAD 模型加载失败: {e}") from e

    def _detect_speech(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        使用 Silero-VAD 检测语音活动

        Args:
            audio_chunk: 音频数据（numpy数组，单声道）
            sample_rate: 采样率

        Returns:
            bool: True表示检测到语音，False表示静音
        """
        if self._vad_model is None:
            self._load_vad()

        try:
            # 转换为 torch tensor
            audio_tensor = torch.from_numpy(audio_chunk).float()

            # 归一化到 [-1, 1]
            if audio_tensor.abs().max() > 1.0:
                audio_tensor = audio_tensor / audio_tensor.abs().max()

            # VAD 推理
            with torch.no_grad():
                speech_prob = self._vad_model(audio_tensor, sample_rate).item()

            return speech_prob > self._vad_threshold

        except Exception as e:
            log.warning(f"VAD 检测失败: {e}")
            return True  # 失败时假设有语音，避免丢失音频

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        转写音频数据

        Args:
            audio_data: 音频数据（numpy数组，单声道，float32）
            sample_rate: 采样率

        Returns:
            dict: 包含 text（识别文本）、language（检测语言）、confidence（置信度）
        """
        self._ensure_model()

        if self._model is None:
            raise ASRError("模型未加载")

        try:
            # 归一化音频到 [-1, 1]
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            max_val = np.abs(audio_data).max()
            if max_val > 1.0:
                audio_data = audio_data / max_val
            elif max_val == 0:
                log.warning("音频数据全为零（静音），返回空结果")
                return {
                    "text": "",
                    "language": self._language or "zh",
                    "confidence": 0.0
                }

            # 调用 Faster-Whisper 转写
            segments, info = self._model.transcribe(
                audio_data,
                language=self._language if self._language else None,
                beam_size=self._beam_size,
                best_of=self._best_of,
                patience=self._patience,
                initial_prompt=self._initial_prompt if self._initial_prompt else None,
                suppress_tokens=self._suppress_tokens if self._suppress_tokens else None,
                vad_filter=False,  # 我们使用自己的VAD
                word_timestamps=False
            )

            # 拼接所有片段
            text_segments = []
            total_confidence = 0.0
            segment_count = 0

            for segment in segments:
                text_segments.append(segment.text.strip())
                total_confidence += segment.avg_logprob
                segment_count += 1

            text = " ".join(text_segments).strip()
            confidence = total_confidence / segment_count if segment_count > 0 else 0.0

            log.info(f"ASR 转写完成: {text[:50]}... (confidence={confidence:.2f})")

            return {
                "text": text,
                "language": info.language,
                "confidence": confidence
            }

        except Exception as e:
            log.error(f"ASR 转写失败: {e}", exc_info=True)
            raise ASRError(f"转写失败: {e}") from e

    def transcribe_file(self, file_path: str) -> dict:
        """
        转写音频文件

        Args:
            file_path: 音频文件路径（支持 wav/mp3/m4a 等格式）

        Returns:
            dict: 包含 text、language、confidence
        """
        try:
            import soundfile as sf
        except ImportError as e:
            raise ASRError("soundfile 未安装，请运行: pip install soundfile") from e

        try:
            # 读取音频文件
            audio_data, sample_rate = sf.read(file_path, dtype='float32')

            # 转换为单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # 重采样到 16kHz（如果需要）
            if sample_rate != 16000:
                log.info(f"重采样音频: {sample_rate}Hz -> 16000Hz")
                try:
                    import librosa
                    audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                    sample_rate = 16000
                except ImportError:
                    log.warning("librosa 未安装，无法重采样，使用原始采样率")

            return self.transcribe(audio_data, sample_rate)

        except Exception as e:
            log.error(f"文件转写失败: {e}", exc_info=True)
            raise ASRError(f"文件转写失败: {e}") from e

    def start_realtime(self, device: Optional[str], on_result_callback: Callable):
        """
        启动实时语音识别

        Args:
            device: 音频输入设备索引或名称（None 表示使用默认设备）
            on_result_callback: 识别结果回调函数，签名为 callback(text: str, language: str, confidence: float)
        """
        with self._realtime_lock:
            if self._realtime_thread is not None and self._realtime_thread.is_alive():
                log.warning("实时识别已在运行中")
                return

            # 确保模型和VAD已加载
            self._ensure_model()
            self._load_vad()

            # 初始化音频缓冲区
            self._audio_buffer = AudioBuffer(sample_rate=16000, vad_threshold=self._vad_threshold)
            self._realtime_stop_event.clear()

            # 启动采集线程
            self._realtime_thread = threading.Thread(
                target=self._realtime_worker,
                args=(device, on_result_callback),
                daemon=True
            )
            self._realtime_thread.start()
            log.info(f"实时识别已启动，设备: {device}")

    def stop_realtime(self):
        """停止实时语音识别"""
        with self._realtime_lock:
            if self._realtime_thread is None or not self._realtime_thread.is_alive():
                log.warning("实时识别未运行")
                return

            # 设置停止事件
            self._realtime_stop_event.set()

            # 等待线程退出（最多等待3秒）
            self._realtime_thread.join(timeout=3.0)
            if self._realtime_thread.is_alive():
                log.warning("实时识别线程未能在3秒内退出")

            # 清理资源
            if self._audio_buffer is not None:
                self._audio_buffer.clear()
                self._audio_buffer = None

            self._realtime_thread = None
            log.info("实时识别已停止")

    def _realtime_worker(self, device: Optional[str], on_result_callback: Callable):
        """实时识别工作线程"""
        try:
            import sounddevice as sd
        except ImportError as e:
            log.error("sounddevice 未安装，无法启动实时识别")
            return

        sample_rate = 16000
        block_size = int(sample_rate * 0.1)  # 100ms per chunk

        def audio_callback(indata, frames, time_info, status):
            """音频流回调函数"""
            if status:
                log.warning(f"音频流状态: {status}")

            # 转换为单声道 float32
            audio_chunk = indata[:, 0].astype(np.float32)

            # VAD 检测
            is_speech = self._detect_speech(audio_chunk, sample_rate)

            # 添加到缓冲区
            should_transcribe = self._audio_buffer.add_chunk(audio_chunk, is_speech)

            # 如果检测到句子结束，进行转写
            if should_transcribe:
                audio_data = self._audio_buffer.get_audio()
                if audio_data is not None and len(audio_data) > 0:
                    try:
                        result = self.transcribe(audio_data, sample_rate)
                        if result["text"]:
                            on_result_callback(
                                result["text"],
                                result["language"],
                                result["confidence"]
                            )
                    except Exception as e:
                        log.error(f"转写失败: {e}", exc_info=True)

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                blocksize=block_size,
                callback=audio_callback,
                device=device
            ):
                log.info("音频流已启动，等待语音输入...")
                while not self._realtime_stop_event.is_set():
                    self._realtime_stop_event.wait(timeout=0.1)

        except Exception as e:
            log.error(f"实时识别异常: {e}", exc_info=True)
        finally:
            log.info("实时识别工作线程退出")

    def shutdown(self):
        """关闭引擎，释放资源"""
        # 先停止实时识别
        self.stop_realtime()

        with self._lock:
            if self._model is not None:
                log.info("关闭 ASR 引擎")
                self._model = None
            if self._vad_model is not None:
                self._vad_model = None

