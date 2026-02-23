"""ASR 设备与麦克风测试 API"""
import threading
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    np = None
    sd = None
from flask import Blueprint, jsonify, request
from src.backend.core.logger import get_logger

log = get_logger("api.asr")

asr_bp = Blueprint("asr", __name__, url_prefix="/api/asr")

_mic_test_stop = threading.Event()
_mic_test_lock = threading.Lock()


@asr_bp.route("/devices")
def list_input_devices():
    devices = sd.query_devices()
    result = [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices) if d["max_input_channels"] > 0
    ]
    return jsonify(result)


@asr_bp.route("/output-devices")
def list_output_devices():
    devices = sd.query_devices()
    result = [
        {"index": i, "name": d["name"], "channels": d["max_output_channels"]}
        for i, d in enumerate(devices) if d["max_output_channels"] > 0
    ]
    return jsonify(result)


@asr_bp.route("/mic-test", methods=["POST"])
def mic_test():
    if not _mic_test_lock.acquire(blocking=False):
        return jsonify({"status": "already_testing"}), 409
    from src.backend.app import socketio
    device = request.json.get("device", None) if request.json else None
    duration = 5
    sr = 16000
    _mic_test_stop.clear()
    _level_box = [0]

    def _run():
        try:
            def callback(indata, frames, time_info, status):
                _level_box[0] = min(100, int(float(np.sqrt(np.mean(indata ** 2))) * 10000))

            with sd.InputStream(samplerate=sr, channels=1, blocksize=int(sr * 0.1),
                                callback=callback, device=device):
                for _ in range(duration * 10):
                    if _mic_test_stop.is_set():
                        break
                    socketio.emit("mic_level", {"level": _level_box[0]}, namespace="/ws/events")
                    socketio.sleep(0.1)
            socketio.emit("mic_level", {"level": -1}, namespace="/ws/events")
        except Exception as e:
            log.exception("麦克风测试异常")
            socketio.emit("mic_level", {"level": -1, "error": str(e)}, namespace="/ws/events")
        finally:
            _mic_test_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "testing", "duration": duration})


@asr_bp.route("/mic-test-stop", methods=["POST"])
def mic_test_stop():
    _mic_test_stop.set()
    return jsonify({"status": "stopped"})
