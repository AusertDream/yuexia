"""
YueXia Launcher - Windows 平台启动脚本
替代原有的 bat 脚本，统一管理 TTS、Backend、Frontend 三个服务的生命周期。
仅依赖标准库 + PyYAML。
"""

import os
import sys
import signal
import shutil
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

import yaml

# ---------------------------------------------------------------------------
# 全局变量
# ---------------------------------------------------------------------------
_processes: dict = {"tts": None, "backend": None, "frontend": None}
_log_files: list = []
_shutting_down: bool = False


# ---------------------------------------------------------------------------
# load_ports
# ---------------------------------------------------------------------------
def load_ports() -> dict:
    """从 config/config.yaml 读取三个服务的端口号。"""
    config_path = Path(os.environ["YUEXIA_ROOT"]) / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    server = cfg["server"]
    return {
        "tts": server["tts_port"],
        "backend": server["backend_port"],
        "frontend": server["frontend_port"],
    }


# ---------------------------------------------------------------------------
# ensure_dirs
# ---------------------------------------------------------------------------
def ensure_dirs():
    """创建项目运行所需的数据目录。"""
    root = Path(os.environ["YUEXIA_ROOT"])
    for d in [
        "data/screenshots",
        "data/tts_output",
        "data/diary",
        "data/chromadb",
        "logs",
    ]:
        (root / d).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# setup_log_dir
# ---------------------------------------------------------------------------
def setup_log_dir() -> Path:
    """在 logs/ 下创建带时间戳的子目录，并清理旧日志（保留最新 5 个）。"""
    root = Path(os.environ["YUEXIA_ROOT"])
    logs_root = root / "logs"
    log_dir = logs_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)

    subdirs = sorted(
        [d for d in logs_root.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    while len(subdirs) > 5:
        old = subdirs.pop(0)
        shutil.rmtree(old, ignore_errors=True)

    return log_dir


# ---------------------------------------------------------------------------
# open_log
# ---------------------------------------------------------------------------
def open_log(log_dir: Path, name: str):
    """打开日志文件用于写入，并记录文件句柄以便 shutdown 时关闭。"""
    f = open(log_dir / name, "w", encoding="utf-8")
    _log_files.append(f)
    return f


# ---------------------------------------------------------------------------
# start_tts
# ---------------------------------------------------------------------------
def start_tts(ports: dict, log_dir: Path) -> subprocess.Popen:
    """启动 GPT-SoVITS TTS 服务。"""
    root = Path(os.environ["YUEXIA_ROOT"])
    sovits_dir = root / "GPT-SoVITS-v2-240821"
    python_exe = sovits_dir / "runtime" / "python.exe"
    port = ports["tts"]

    print(f"[YueXia] Starting TTS service (port {port})...")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    log_f = open_log(log_dir, "tts.log")
    proc = subprocess.Popen(
        [
            str(python_exe),
            "api_v2.py",
            "-a", "127.0.0.1",
            "-p", str(port),
            "-c", "GPT_SoVITS/configs/tts_infer.yaml",
        ],
        cwd=str(sovits_dir),
        stdout=log_f,
        stderr=log_f,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return proc


# ---------------------------------------------------------------------------
# start_backend
# ---------------------------------------------------------------------------
def start_backend(ports: dict, log_dir: Path) -> subprocess.Popen:
    """启动后端服务。"""
    root = Path(os.environ["YUEXIA_ROOT"])
    port = ports["backend"]

    print(f"[YueXia] Starting Backend service (port {port})...")

    env = os.environ.copy()
    env["YUEXIA_ROOT"] = str(root)
    env["PYTHONIOENCODING"] = "utf-8"

    log_f = open_log(log_dir, "backend.log")
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.backend.app"],
        cwd=str(root),
        stdout=log_f,
        stderr=log_f,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return proc


# ---------------------------------------------------------------------------
# start_frontend
# ---------------------------------------------------------------------------
def start_frontend(ports: dict, log_dir: Path) -> subprocess.Popen:
    """启动前端服务。"""
    root = Path(os.environ["YUEXIA_ROOT"])
    frontend_dir = root / "src" / "frontend"
    port = ports["frontend"]

    print(f"[YueXia] Starting Frontend service (port {port})...")

    env = os.environ.copy()
    env["VITE_BACKEND_PORT"] = str(ports["backend"])
    env["VITE_FRONTEND_PORT"] = str(ports["frontend"])
    env["PYTHONIOENCODING"] = "utf-8"

    log_f = open_log(log_dir, "frontend.log")
    proc = subprocess.Popen(
        ["npm.cmd", "run", "dev"],
        cwd=str(frontend_dir),
        stdout=log_f,
        stderr=log_f,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return proc


# ---------------------------------------------------------------------------
# wait_frontend
# ---------------------------------------------------------------------------
def wait_frontend(port: int) -> bool:
    """轮询前端服务是否就绪，最多等待 60 秒。同时检查所有子进程是否存活。"""
    url = f"http://localhost:{port}"
    for _ in range(30):
        for name, proc in _processes.items():
            if proc is not None and proc.poll() is not None:
                print(f"[YueXia] ERROR: {name} process crashed (exit code {proc.returncode})")
                return False
        try:
            urlopen(url, timeout=2)
            return True
        except (URLError, OSError):
            time.sleep(2)
    print("[YueXia] ERROR: Frontend did not respond within 60 seconds")
    return False


# ---------------------------------------------------------------------------
# find_pids_by_keyword
# ---------------------------------------------------------------------------
def find_pids_by_keyword(keyword: str) -> set:
    """通过命令行关键字查找进程 PID。"""
    try:
        cmd = (
            'powershell -NoProfile -Command "'
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{$_.CommandLine -like '*{keyword}*'}} | "
            'ForEach-Object {$_.ProcessId}"'
        )
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        pids = set()
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
        return pids
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# find_pids_by_port
# ---------------------------------------------------------------------------
def find_pids_by_port(port: int) -> set:
    """通过端口号查找占用该端口的进程 PID。"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        pids = set()
        target = f":{port} "
        for line in result.stdout.splitlines():
            if target in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid_str = parts[-1].strip()
                    if pid_str.isdigit() and int(pid_str) != 0:
                        pids.add(int(pid_str))
        return pids
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# kill_service
# ---------------------------------------------------------------------------
def kill_service(name: str, keyword: str, port: int, proc=None):
    """安全关闭指定服务进程，保留原 bat 的全部安全机制。"""
    if not keyword or not port:
        print(f"[YueXia] Skipping {name} (no keyword or port)")
        return

    # 检查端口是否被占用
    port_pids = find_pids_by_port(port)
    if not port_pids:
        print(f"[YueXia] {name} is not running (port {port} free)")
        return

    # 通过关键字和端口分别查找 PID，取交集
    name_pids = find_pids_by_keyword(keyword)
    common_pids = name_pids & port_pids

    # 安全检查：交集超过 4 个 PID 则中止
    if len(common_pids) > 4:
        print(f"[YueXia] WARNING: Too many PIDs ({len(common_pids)}) matched for {name}, aborting kill")
        return

    # 精确杀死交集中的进程
    if common_pids:
        for pid in common_pids:
            print(f"[YueXia] Killing {name} process (PID {pid})...")
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        return

    # 交集为空时回退到 Popen 对象
    if proc is not None and proc.poll() is None:
        print(f"[YueXia] Terminating {name} via Popen...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"[YueXia] {name} terminated")


# ---------------------------------------------------------------------------
# shutdown_all
# ---------------------------------------------------------------------------
def shutdown_all(ports: dict):
    """关闭所有服务并清理资源。"""
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    print("[YueXia] Stopping services...")

    kill_service("TTS", "api_v2.py", ports["tts"], _processes.get("tts"))
    kill_service("Backend", "src.backend.app", ports["backend"], _processes.get("backend"))
    kill_service("Frontend", "vite", ports["frontend"], _processes.get("frontend"))

    for f in _log_files:
        try:
            f.close()
        except Exception:
            pass

    print("[YueXia] All services stopped. Goodbye!")


# ---------------------------------------------------------------------------
# interactive_menu
# ---------------------------------------------------------------------------
def interactive_menu(ports: dict):
    """显示交互菜单，等待用户操作。"""
    frontend_url = f"http://localhost:{ports['frontend']}"
    while True:
        print()
        print("============================================")
        print("  [YueXia] All services running!")
        print("============================================")
        print("  1. Open browser")
        print("  2. Exit (close all services)")
        print("============================================")
        try:
            choice = input("  Enter choice: ").strip()
        except EOFError:
            shutdown_all(ports)
            return
        if choice == "1":
            webbrowser.open(frontend_url)
        elif choice == "2":
            shutdown_all(ports)
            return
        else:
            print("[!!] Invalid choice.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    """入口函数：初始化环境、启动服务、进入交互菜单。"""
    global _processes

    ROOT = Path(__file__).resolve().parent
    os.environ["YUEXIA_ROOT"] = str(ROOT)

    ports = load_ports()
    ensure_dirs()
    log_dir = setup_log_dir()

    # 注册信号处理
    def _signal_handler(sig, frame):
        shutdown_all(ports)
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGBREAK, _signal_handler)

    # 启动 TTS
    _processes["tts"] = start_tts(ports, log_dir)
    print("[YueXia] Waiting 5s for TTS initialization...")
    time.sleep(5)

    # 启动 Backend
    _processes["backend"] = start_backend(ports, log_dir)

    # 启动 Frontend
    _processes["frontend"] = start_frontend(ports, log_dir)

    # 等待前端就绪
    print("[YueXia] Waiting for frontend to be ready...")
    if not wait_frontend(ports["frontend"]):
        shutdown_all(ports)
        sys.exit(1)

    frontend_url = f"http://localhost:{ports['frontend']}"
    print(f"[YueXia] All services ready! Opening {frontend_url}")
    webbrowser.open(frontend_url)

    interactive_menu(ports)


if __name__ == "__main__":
    main()
