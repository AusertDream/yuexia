"""ASR 设备与麦克风测试 API"""
import threading
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    np = None
    sd = None
from flask import Blueprint, jsonify, request

asr_bp = Blueprint("asr", __name__, url_prefix="/api/asr")

_mic_test_stop = threading.Event()


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
    from src.backend.app import socketio
    device = request.json.get("device", None) if request.json else None
    duration = 5
    sr = 16000
    _mic_test_stop.clear()

    def _run():
        try:
            def callback(indata, frames, time_info, status):
                rms = float(np.sqrt(np.mean(indata ** 2)))
                level = min(100, int(rms * 10000))
                socketio.emit("mic_level", {"level": level}, namespace="/ws/events")

            with sd.InputStream(samplerate=sr, channels=1, blocksize=int(sr * 0.1),
                                callback=callback, device=device):
                for _ in range(duration * 10):
                    if _mic_test_stop.is_set():
                        break
                    socketio.sleep(0.1)
            socketio.emit("mic_level", {"level": -1}, namespace="/ws/events")
        except Exception as e:
            socketio.emit("mic_level", {"level": -1, "error": str(e)}, namespace="/ws/events")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "testing", "duration": duration})


@asr_bp.route("/mic-test-stop", methods=["POST"])
def mic_test_stop():
    _mic_test_stop.set()
    return jsonify({"status": "stopped"})
