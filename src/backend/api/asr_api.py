"""ASR 设备与麦克风测试 API"""
import asyncio
import re
import time
import threading
from typing import TYPE_CHECKING
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    np = None
    sd = None
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from src.backend.core.logger import get_logger

if TYPE_CHECKING:
    from src.backend.services.perception_service import PerceptionService

log = get_logger("api.asr")

asr_router = APIRouter(prefix="/api/asr")

_mic_test_stop = threading.Event()
_mic_test_lock = threading.Lock()

# 驱动接口优先级：WASAPI > DirectSound > MME
_DRIVER_PRIORITY = {"Windows WASAPI": 3, "Windows DirectSound": 2, "MME": 1}
# 预编译正则表达式，避免每次调用都重新编译
_DRIVER_SUFFIX_PATTERN = re.compile(r'\s*-\s*(MME|Windows WASAPI|Windows DirectSound|ASIO).*$')


def get_perception_service():
    """获取感知服务实例（延迟导入避免循环依赖）"""
    from src.backend.services import perception_service
    if perception_service is None:
        raise HTTPException(status_code=503, detail="感知服务未初始化")
    return perception_service


def _get_driver_priority(device_name):
    """提取设备驱动优先级"""
    for driver, priority in _DRIVER_PRIORITY.items():
        if driver in device_name:
            return priority
    return 0


def _deduplicate_devices(devices):
    """智能去重音频设备列表，优先保留WASAPI接口"""
    seen_names = {}
    result = []

    for device in devices:
        base_name = _DRIVER_SUFFIX_PATTERN.sub('', device['name'])

        if base_name not in seen_names:
            seen_names[base_name] = device
            result.append(device)
        else:
            existing = seen_names[base_name]
            existing_priority = _get_driver_priority(existing['name'])
            current_priority = _get_driver_priority(device['name'])
            if current_priority > existing_priority:
                result = [d for d in result if d['index'] != existing['index']]
                seen_names[base_name] = device
                result.append(device)

    filtered_count = len(devices) - len(result)
    if filtered_count > 0:
        log.debug(f"设备去重: {len(devices)} -> {len(result)} (过滤了 {filtered_count} 个重复设备)")
    else:
        log.debug(f"设备去重: {len(devices)} 个设备，无重复")
    return result


@asr_router.get("/devices")
async def list_input_devices():
    if sd is None:
        return JSONResponse(content={"error": "sounddevice 未安装，无法获取音频设备列表"}, status_code=503)
    devices = sd.query_devices()
    result = [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices) if d["max_input_channels"] > 0
    ]
    return JSONResponse(content=_deduplicate_devices(result))


@asr_router.get("/devices/raw")
async def list_input_devices_raw():
    """返回未去重的原始设备列表（供调试使用）"""
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
    return JSONResponse(content=_deduplicate_devices(result))


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


@asr_router.post("/transcribe")
async def transcribe_audio_file(
    request: Request,
    perception_svc = Depends(get_perception_service)
):
    """
    转写上传的音频文件

    支持格式：wav/mp3/m4a
    文件大小限制：10MB
    """
    from src.backend.perception.asr import ASRError
    import tempfile
    import os

    try:
        # 解析 multipart/form-data
        form = await request.form()
        audio_file = form.get("file")

        if not audio_file:
            return JSONResponse(content={"error": "未提供音频文件"}, status_code=400)

        # 流式读取并检查文件大小（10MB限制）
        content = bytearray()
        chunk_size = 1024 * 1024  # 1MB chunks
        max_size = 10 * 1024 * 1024  # 10MB

        while True:
            chunk = await audio_file.read(chunk_size)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > max_size:
                return JSONResponse(
                    content={"error": "文件大小超过10MB限制"},
                    status_code=400
                )

        # 检查文件格式
        filename = audio_file.filename
        if not filename:
            return JSONResponse(content={"error": "文件名无效"}, status_code=400)

        ext = filename.lower().split(".")[-1]
        if ext not in ["wav", "mp3", "m4a", "flac", "ogg"]:
            return JSONResponse(content={"error": f"不支持的文件格式: {ext}"}, status_code=400)

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # 调用ASR转写
            import time
            start_time = time.time()
            result = await perception_svc.transcribe_file(tmp_path)
            processing_time = time.time() - start_time

            return JSONResponse(content={
                "text": result["text"],
                "language": result["language"],
                "confidence": result["confidence"],
                "processing_time": round(processing_time, 2)
            })

        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except ASRError as e:
        log.error(f"ASR 转写失败: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    except Exception as e:
        log.exception("音频转写异常")
        return JSONResponse(content={"error": f"转写失败: {str(e)}"}, status_code=500)


@asr_router.post("/start")
async def start_realtime_asr(
    request: Request,
    perception_svc = Depends(get_perception_service)
):
    """启动实时ASR会话"""
    try:
        # JSON 解析错误处理
        try:
            data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        except Exception as json_err:
            log.warning(f"JSON 解析失败: {json_err}")
            return JSONResponse(
                content={"error": "无效的 JSON 格式"},
                status_code=400
            )

        device = data.get("device", None)
        mode = data.get("mode", "vad")  # vad 或 push_to_talk

        # 调用服务层启动（竞态条件检查移到服务层内部）
        result = await perception_svc.start_realtime_asr(device)

        if result is False:
            return JSONResponse(
                content={"error": "实时ASR会话已在运行中"},
                status_code=409
            )

        return JSONResponse(content={
            "status": "started",
            "device": device,
            "mode": mode
        })

    except Exception as e:
        log.exception("启动实时ASR失败")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@asr_router.post("/stop")
async def stop_realtime_asr(perception_svc = Depends(get_perception_service)):
    """停止实时ASR会话"""
    try:
        await perception_svc.stop_realtime_asr()
        return JSONResponse(content={"status": "stopped"})

    except Exception as e:
        log.exception("停止实时ASR失败")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@asr_router.get("/status")
async def get_asr_status(perception_svc = Depends(get_perception_service)):
    """获取ASR状态"""
    try:
        return JSONResponse(content={
            "realtime_active": perception_svc._realtime_asr_active,
            "model_loaded": perception_svc.asr._model is not None,
            "device": perception_svc.asr._device
        })

    except Exception as e:
        log.exception("获取ASR状态失败")
        return JSONResponse(content={"error": str(e)}, status_code=500)

