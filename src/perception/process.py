"""Perception 子进程入口"""
from __future__ import annotations
import asyncio
import multiprocessing as mp
from src.core.bus import AsyncQueueBridge
from src.core.config import load_config
from src.core.message import Message, MessageType
from src.core.logger import get_logger

log = get_logger("perception.process")


async def _run(bridge: AsyncQueueBridge, face_bridge: AsyncQueueBridge | None = None):
    from src.perception.asr import ASREngine
    from src.perception.tts import TTSEngine

    asr = ASREngine()
    tts = TTSEngine()

    async def on_asr_text(text: str):
        log.info(f"ASR 识别: {text}")
        await bridge.send(Message(
            type=MessageType.ASR_RESULT,
            source="perception", target="brain",
            payload={"text": text},
        ))

    asr_task = asyncio.create_task(asr.start_listening(on_asr_text))
    asr_task.add_done_callback(
        lambda t: log.error(f"ASR task 异常退出: {t.exception()}") if not t.cancelled() and t.exception() else None
    )

    async def _poll_face():
        if not face_bridge:
            return
        while True:
            msg = await face_bridge.recv()
            if msg:
                await _handle_mic(msg, asr, face_bridge)
            await asyncio.sleep(0.01)

    face_task = asyncio.create_task(_poll_face())

    try:
        while True:
            msg = await bridge.recv()
            if msg:
                if msg.type == MessageType.TTS_REQUEST:
                    text = msg.payload.get("text", "")
                    emotion = msg.payload.get("emotion", "neutral")
                    msg_index = msg.payload.get("msg_index", -1)
                    path = await tts.synthesize(text, emotion)
                    if path:
                        await bridge.send(Message(
                            type=MessageType.TTS_DONE,
                            source="perception", target="face",
                            payload={"path": path, "msg_index": msg_index},
                        ))
                elif msg.type == MessageType.CONFIG_RELOAD:
                    from src.core.config import reload_config, get
                    reload_config()
                    asr.set_mode(get("perception.asr.mic_mode", "always_on"))
                    log.info("Perception 配置已热更新")
                elif msg.type == MessageType.SHUTDOWN:
                    break
            await asyncio.sleep(0.01)
    finally:
        asr.stop()
        asr_task.cancel()
        face_task.cancel()


async def _handle_mic(msg: Message, asr, face_bridge: AsyncQueueBridge):
    if msg.type == MessageType.MIC_MODE_CHANGE:
        asr.set_mode(msg.payload.get("mode", "always_on"))
    elif msg.type == MessageType.MIC_START_RECORDING:
        asr.start_ptt()
    elif msg.type == MessageType.MIC_STOP_RECORDING:
        asr.stop_ptt()
    elif msg.type == MessageType.MIC_TEST_REQUEST:
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, asr.mic_test)
        await face_bridge.send(Message(
            type=MessageType.MIC_TEST_RESULT,
            source="perception", target="face",
            payload={"path": path},
        ))


def perception_main(inbound: mp.Queue, outbound: mp.Queue, config_path: str = "config.yaml",
                    log_queue: mp.Queue | None = None,
                    face_inbound: mp.Queue | None = None, face_outbound: mp.Queue | None = None):
    load_config(config_path)
    if log_queue:
        from src.core.logger import setup_queue_logging
        setup_queue_logging(log_queue)
    log.info("Perception 进程启动")
    bridge = AsyncQueueBridge(inbound, outbound)
    face_bridge = AsyncQueueBridge(face_inbound, face_outbound) if face_inbound and face_outbound else None
    asyncio.run(_run(bridge, face_bridge))
    log.info("Perception 进程退出")
