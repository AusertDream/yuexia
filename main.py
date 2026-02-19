import asyncio
import ctypes
import multiprocessing as mp
import signal
import sys
from src.core.config import load_config
from src.core.bus import AsyncQueueBridge
from src.core.message import Message, MessageType
from src.core.logger import get_logger, setup_queue_logging

log = get_logger("main")


def main():
    config = load_config("config.yaml")
    log.info("系统启动中...")

    # 创建 3 对 Queue (每对: brain->子进程, 子进程->brain)
    face_to_brain, brain_to_face = mp.Queue(), mp.Queue()
    perc_to_brain, brain_to_perc = mp.Queue(), mp.Queue()
    act_to_brain, brain_to_act = mp.Queue(), mp.Queue()
    # Face <-> Perception 直连（麦克风控制）
    face_to_perc, perc_to_face = mp.Queue(), mp.Queue()
    log_queue = mp.Queue()

    # Brain 主进程也把日志发到 log_queue
    setup_queue_logging(log_queue)

    # 启动子进程
    from src.face.process import face_main
    from src.perception.process import perception_main
    from src.action.process import action_main

    # Face 进程（不重启）
    face_proc = mp.Process(target=face_main, args=(brain_to_face, face_to_brain, "config.yaml", log_queue, perc_to_face, face_to_perc), name="face")
    face_proc.daemon = True
    face_proc.start()
    log.info(f"子进程已启动: {face_proc.name} (pid={face_proc.pid})")

    # 可重启的服务进程
    svc_procs: list[mp.Process] = []

    def start_services():
        nonlocal svc_procs
        svc_procs = [
            mp.Process(target=perception_main, args=(brain_to_perc, perc_to_brain, "config.yaml", log_queue, face_to_perc, perc_to_face), name="perception"),
            mp.Process(target=action_main, args=(brain_to_act, act_to_brain, "config.yaml", log_queue), name="action"),
        ]
        for p in svc_procs:
            p.daemon = True
            p.start()
            log.info(f"子进程已启动: {p.name} (pid={p.pid})")

    def restart_services():
        for q in [brain_to_perc, brain_to_act]:
            q.put(Message(type=MessageType.SHUTDOWN, source="main").model_dump())
        for p in svc_procs:
            p.join(timeout=3)
            if p.is_alive():
                p.terminate()
        for q in [perc_to_brain, act_to_brain]:
            while not q.empty():
                try:
                    q.get_nowait()
                except Exception:
                    break
        start_services()
        log.info("服务进程已重启")

    start_services()

    # 隐藏 CMD 控制台窗口（日志已转到 app 内控制台）
    if sys.platform == "win32":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)

    # Brain 主进程
    from src.brain.brain import Brain

    face_bridge = AsyncQueueBridge(face_to_brain, brain_to_face)
    perc_bridge = AsyncQueueBridge(perc_to_brain, brain_to_perc)
    act_bridge = AsyncQueueBridge(act_to_brain, brain_to_act)

    brain = Brain(face_bridge, perc_bridge, act_bridge)
    brain._restart_services = restart_services

    def shutdown(sig, frame):
        log.info("收到退出信号")
        for q in [brain_to_face, brain_to_perc, brain_to_act]:
            q.put(Message(type=MessageType.SHUTDOWN, source="main").model_dump())
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        asyncio.run(brain.run())
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
