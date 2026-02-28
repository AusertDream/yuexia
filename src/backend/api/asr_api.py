"""ASR 设备与麦克风测试 API"""
import asyncio
import time
import threading
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    np = None
    sd = None
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.backend.core.logger import get_logger

log = get_logger("api.asr")

asr_router = APIRouter(prefix="/api/asr")

_mic_test_stop = threading.Event()
_mic_test_lock = threading.Lock()


@asr_router.get("/devices")
async def list_input_devices():
    if sd is None:
        return JSONResponse(content={"error": "sounddevice 未安装，无法获取音频设备列表"}, status_code=503)
    devices = sd.query_devices()
    result = [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices) if d["max_input_channels"] > 0
    ]
    return JSONResponse(content=result)


@asr_router.get("/output-devices")
async def list_output_devices():
    if sd is None:
        return JSONResponse(content={"error": "sounddevice 未安装，无法获取音频设备列表"}, status_code=503)
    devices = sd.query_devices()
    result = [
        {"index": i, "name": d["name"], "channels": d["max_output_channels"]}
        for i, d in enumerate(devices) if d["max_output_channels"] > 0
    ]
    return JSONResponse(content=result)


@asr_router.post("/mic-test")
async def mic_test(request: Request):
    if sd is None or np is None:
        return JSONResponse(content={"error": "sounddevice/numpy 未安装，无法进行麦克风测试"}, status_code=503)
    if not _mic_test_lock.acquire(blocking=False):
        return JSONResponse(content={"status": "already_testing"}, status_code=409)
    from src.backend.app import sio
    data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else None
    device = data.get("device", None) if data else None
    duration = 5
    sr = 16000
    _mic_test_stop.clear()
    _level_box = [0]

    def _emit_async(event, data):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    sio.emit(event, data, namespace="/ws/events"), loop
                )
            else:
                loop.run_until_complete(sio.emit(event, data, namespace="/ws/events"))
        except Exception:
            log.warning(f"发送 {event} 事件失败", exc_info=True)

    def _run():
        try:
            def callback(indata, frames, time_info, status):
                _level_box[0] = min(100, int(float(np.sqrt(np.mean(indata ** 2))) * 10000))

            with sd.InputStream(samplerate=sr, channels=1, blocksize=int(sr * 0.1),
                                callback=callback, device=device):
                for _ in range(duration * 10):
                    if _mic_test_stop.is_set():
                        break
                    _emit_async("mic_level", {"level": _level_box[0]})
                    time.sleep(0.1)
            _emit_async("mic_level", {"level": -1})
        except Exception as e:
            log.exception("麦克风测试异常")
            _emit_async("mic_level", {"level": -1, "error": str(e)})
        finally:
            _mic_test_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse(content={"status": "testing", "duration": duration})


@asr_router.post("/mic-test-stop")
async def mic_test_stop():
    _mic_test_stop.set()
    return JSONResponse(content={"status": "stopped"})
