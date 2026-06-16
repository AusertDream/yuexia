#!/usr/bin/env bash
# ============================================================================
# YueXia 容器启动脚本（Linux 版，替代 Windows 专用的 launcher.py）
# 职责：覆写模型路径 -> 建数据目录 -> 起 TTS(可选) -> 起后端 -> 起前端 -> 优雅退出
# ============================================================================
set -euo pipefail

ROOT=/app
export YUEXIA_ROOT="$ROOT"
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1

BACKEND_PY=/opt/venv-backend/bin/python
TTS_PY=/opt/venv-tts/bin/python

CONFIG="$ROOT/config/config.yaml"
LOG_DIR="$ROOT/logs/docker"
mkdir -p "$LOG_DIR"

# 可由 compose 环境变量覆盖的运行参数
MODEL_PATH="${BRAIN_MODEL_PATH:-/models/llm}"
START_TTS="${START_TTS:-1}"
TTS_PORT="${TTS_PORT:-9880}"

log() { echo "[entrypoint] $*"; }

# ---------------------------------------------------------------------------
# 1. 把 config.yaml 里的 brain.model_path 覆写成容器内挂载路径（不写死宿主机绝对路径）
#    仅当挂载点确实存在模型文件时才覆写，避免空挂载导致后端报错
# ---------------------------------------------------------------------------
if [ -d "$MODEL_PATH" ] && [ -n "$(ls -A "$MODEL_PATH" 2>/dev/null)" ]; then
    log "Overriding brain.model_path -> $MODEL_PATH"
    "$BACKEND_PY" - "$CONFIG" "$MODEL_PATH" <<'PYEOF'
import sys, yaml
cfg_path, model_path = sys.argv[1], sys.argv[2]
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
cfg.setdefault("brain", {})["model_path"] = model_path
with open(cfg_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
print("[entrypoint] config.yaml updated")
PYEOF
else
    log "WARN: model dir '$MODEL_PATH' empty or missing; keeping config.yaml as-is."
    log "      若用本地引擎(transformers/vllm)请在 .env 设置 MODEL_DIR 指向模型目录。"
fi

# ---------------------------------------------------------------------------
# 2. 创建运行时数据目录
# ---------------------------------------------------------------------------
mkdir -p "$ROOT/data/screenshots" "$ROOT/data/tts_output" "$ROOT/data/diary" \
         "$ROOT/data/chromadb" "$ROOT/data/photos" "$ROOT/.runtime"

# ---------------------------------------------------------------------------
# 3. 进程管理与优雅退出
# ---------------------------------------------------------------------------
PIDS=()
cleanup() {
    log "Shutting down services..."
    for pid in "${PIDS[@]:-}"; do
        [ -n "$pid" ] && kill -TERM "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    log "All services stopped."
}
trap cleanup SIGINT SIGTERM EXIT

# ---------------------------------------------------------------------------
# 4. 启动 TTS（GPT-SoVITS，可通过 START_TTS=0 关闭）
# ---------------------------------------------------------------------------
if [ "$START_TTS" = "1" ]; then
    log "Starting TTS (GPT-SoVITS) on 0.0.0.0:$TTS_PORT ..."
    (
        cd "$ROOT/GPT-SoVITS-v2-240821"
        exec "$TTS_PY" api_v2.py -a 0.0.0.0 -p "$TTS_PORT" \
             -c GPT_SoVITS/configs/tts_infer.yaml
    ) >> "$LOG_DIR/tts.log" 2>&1 &
    PIDS+=($!)
    log "Waiting 5s for TTS init..."
    sleep 5
else
    log "START_TTS=0, skip GPT-SoVITS."
fi

# ---------------------------------------------------------------------------
# 5. 启动后端（FastAPI, app.py 内部已 host=0.0.0.0:backend_port）
# ---------------------------------------------------------------------------
log "Starting backend ..."
(
    cd "$ROOT"
    exec "$BACKEND_PY" -m src.backend.app
) >> "$LOG_DIR/backend.log" 2>&1 &
PIDS+=($!)

# ---------------------------------------------------------------------------
# 6. 启动前端（Vite dev，必须 --host 0.0.0.0 才能从容器外访问）
# ---------------------------------------------------------------------------
log "Starting frontend (vite --host 0.0.0.0) ..."
(
    cd "$ROOT/src/frontend"
    export VITE_BACKEND_PORT="${BACKEND_PORT:-5000}"
    export VITE_FRONTEND_PORT="${FRONTEND_PORT:-5173}"
    exec npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT:-5173}"
) >> "$LOG_DIR/frontend.log" 2>&1 &
PIDS+=($!)

log "All services launched. Tailing logs (Ctrl+C to stop)..."
log "  Frontend  -> http://<host-ip>:${FRONTEND_PORT:-5173}"
log "  Backend   -> http://<host-ip>:${BACKEND_PORT:-5000}"

# tail 日志到容器 stdout，方便 docker logs 查看；任一服务退出则容器退出
tail -n +1 -F "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" "$LOG_DIR/tts.log" 2>/dev/null &
PIDS+=($!)

wait -n
log "A service exited; stopping container."
exit 1
