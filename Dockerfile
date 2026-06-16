# ============================================================================
# YueXia 月下 —— 一体化容器镜像
# 基础镜像：NVIDIA CUDA 12.1 runtime on Ubuntu 22.04（本地 LLM/TTS 需要 GPU）
# 镜像内固化：系统依赖 + 两个隔离的 Python venv + 前端 node_modules
# 项目代码本身通过 compose 的 bind mount 挂入，便于在其他机器上免重建直接运行
# ============================================================================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

LABEL maintainer="YueXia"
LABEL description="YueXia all-in-one image: backend + frontend + GPT-SoVITS TTS"

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ---------------------------------------------------------------------------
# 1. 系统依赖：Python 3.11、Node.js 20、ffmpeg（TTS 必需）、构建工具
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common ca-certificates curl gnupg && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-dev \
        python3-pip \
        build-essential git git-lfs \
        ffmpeg libsox-dev \
        tzdata && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch CUDA 12.1 wheel 源（后端与 TTS 两个 venv 共用）
ENV TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121

# ---------------------------------------------------------------------------
# 2. 后端 venv (/opt/venv-backend) —— transformers / fastapi / chromadb 等
#    先单独 COPY requirements 以利用构建缓存
# ---------------------------------------------------------------------------
COPY src/backend/requirements.txt /tmp/backend-requirements.txt
RUN python3.11 -m venv /opt/venv-backend && \
    /opt/venv-backend/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv-backend/bin/pip install --no-cache-dir \
        torch torchvision --index-url ${TORCH_INDEX_URL} && \
    /opt/venv-backend/bin/pip install --no-cache-dir -r /tmp/backend-requirements.txt

# ---------------------------------------------------------------------------
# 3. TTS venv (/opt/venv-tts) —— GPT-SoVITS 的老版本依赖，与后端隔离避免冲突
# ---------------------------------------------------------------------------
COPY GPT-SoVITS-v2-240821/requirements.txt /tmp/tts-requirements.txt
RUN python3.11 -m venv /opt/venv-tts && \
    /opt/venv-tts/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv-tts/bin/pip install --no-cache-dir \
        torch torchvision torchaudio --index-url ${TORCH_INDEX_URL} && \
    /opt/venv-tts/bin/pip install --no-cache-dir -r /tmp/tts-requirements.txt

# ---------------------------------------------------------------------------
# 4. 前端依赖 —— 装进镜像内的 /opt/frontend-node_modules，
#    运行时由 compose 的匿名卷挂到 src/frontend/node_modules，避免被 bind mount 覆盖
# ---------------------------------------------------------------------------
COPY src/frontend/package.json src/frontend/package-lock.json* /tmp/frontend/
RUN cd /tmp/frontend && \
    (npm ci || npm install) && \
    mkdir -p /opt/frontend-node_modules && \
    cp -r /tmp/frontend/node_modules/. /opt/frontend-node_modules/ && \
    rm -rf /tmp/frontend

# ---------------------------------------------------------------------------
# 5. 启动脚本
# ---------------------------------------------------------------------------
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

# 前端 5173 / 后端 5000 / TTS 9880
EXPOSE 5173 5000 9880

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
