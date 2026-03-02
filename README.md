# 月下 (YueXia)

<div align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"/>
  <img src="https://img.shields.io/badge/Python-3.11-green.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform"/>
</div>

---

## 🌙 一个真正属于你的 AI 伴侣

月下是一个完全本地部署的 AI 虚拟伴侣系统，她不仅能与你对话，还能记住你们的每一次交流，用富有情感的声音回应你，甚至会在每天结束时写下属于她的日记。通过 Live2D 角色模型，她拥有生动的视觉形象；通过情感驱动的语音合成，她的每一句话都带着真实的情感色彩。所有数据完全存储在你的设备上，无需担心隐私泄露，真正做到"你的伴侣，只属于你"。

## 画饼

1. 月下应该能够像openclawd那样，浏览网页，使用MCP工具等（拥有四肢），拥有自己的生活。
2. 月下应该说话的时候应该支持live2d实时表情变化，以及动作变化。计划设计一种action，类似VLA那种表示这种变化，同时也为了兼容之后的3D模型。

---

## ✨ 核心特性

**完全本地运行**：所有数据存储在你的设备上，无需担心隐私泄露，支持 Windows 11 + RTX GPU 环境，真正做到数据自主可控。

**真实的情感表达**：基于情感标签的 TTS 系统，根据对话内容动态选择参考音频，让每句话都带着恰当的情感。月下不会用机械的声音回应你，她的每一句话都经过情感池的精心挑选，开心时声音明快，悲伤时语调低沉，就像真实的人类伙伴一样。

**长期记忆能力**：通过 ChromaDB 向量数据库，她能记住你们的对话历史，并在合适的时候回忆起过去的交流。不仅如此，她还会在每次对话后自动生成日记，记录下她的感受和思考，支持日记、周记、月记、年记四种类型，每种类型独立配置。

**自主行为引擎**：支持定时触发、无输入超时触发、cron 表达式触发等多种行为模式，她会主动与你互动，而不仅仅是被动回应。你可以设置安静时段和每日消息限制，让她在合适的时候出现，不会打扰你的工作和休息。

**灵活的推理引擎**：支持 vLLM、Transformers、OpenAI API 三种推理模式，自动根据运行环境选择最优方案（Windows 自动降级至 Transformers），同时支持多模态输入（文本 + 图像）和 SSE 流式对话输出，为用户提供流畅的交互体验。

---

## 🚀 快速开始

### Windows 一键启动（推荐）

👉 双击 `start.bat` 即可启动（TTS + Backend + Frontend 三合一）

⭐ 注意！操作系统必须是 **Windows 10/11**，需要安装 **Python 3.11** 和 **CUDA 13.0**（如果使用 GPU 推理）。

### 通过 launcher.py 启动

```bash
python launcher.py
```

launcher.py 会自动激活 conda 环境、设置环境变量、启动所有服务，并在启动完成后自动打开浏览器。

### 手动启动

```bash
# 激活 conda 环境
conda activate yuexia

# 启动后端（端口 5000）
python -m src.backend.app

# 启动前端（端口 5173）
cd src/frontend && npm run dev

# GPT-SoVITS 需单独启动（端口 9880）
```

### 启动后

浏览器会自动打开 http://localhost:5173，你将看到月下的 Live2D 角色和聊天界面。

---

## 💬 核心能力

### 对话与记忆

月下支持流式对话输出，能够理解文本和图像输入（多模态推理），并通过 ChromaDB 向量数据库记住你们的对话历史。她还会在每次对话后自动生成日记，记录下她的感受和思考。日记系统支持四种类型（日记、周记、月记、年记），每种类型独立配置，你可以随时查看她的内心世界。

### 语音与情感

基于 GPT-SoVITS 的情感驱动 TTS 系统，月下能够根据对话内容动态选择参考音频，用富有情���的声音回应你。支持多种情感标签（开心、悲伤、生气等），每句话都带着恰当的情感色彩。情感音频参考池通过 meta.yaml 配置，自动扫描情感目录，你可以轻松添加自己的情感音频。

### Live2D 角色

通过 PixiJS + Cubism 4 SDK，月下拥有生动的 Live2D 角色模型，支持锁定/解锁交互，并能持久化显示状态。Live2D 角色以全屏背景形式呈现，聊天面板以毛玻璃浮层形式固定在右侧，营造沉浸式的交互体验。未来将支持唇形同步和表情动画，让她的表情随着对话内容实时变化。

### 自主行为

月下不仅仅是被动回应，她还拥有自主行为引擎，支持定时触发、无输入超时触发、cron 表达式触发等多种行为模式，会主动与你互动。你可以设置安静时段（如工作时间、睡眠时间），让她在合适的时候出现，不会打扰你的生活。每日消息限制功能确保她不会过于频繁地打扰你。

### 开发者友好

提供完整的 REST API 和 WebSocket 接口，支持 SSE 流式输出，配置管理页面覆盖 137 个配置项，实时日志系统支持 WebSocket 日志流。所有 API 端点都有详细的 OpenAPI 3.0 规范和 Swagger UI 文档，方便开发者集成和扩展。

---

## 🛠️ 技术栈

| 层      | 技术                                       |
| ------ | ---------------------------------------- |
| 前端     | React 19 + TypeScript + Vite 6 + TailwindCSS 4 + Zustand |
| 后端     | FastAPI + Socket.IO (ASGI)               |
| LLM    | Qwen3-VL-4B-Instruct（vLLM / Transformers / OpenAI API 三模） |
| TTS    | GPT-SoVITS v2（HTTP API）                  |
| ASR    | Faster-Whisper + Silero-VAD              |
| 向量数据库  | ChromaDB                                 |
| Live2D | PixiJS + Cubism 4 SDK                    |
| 任务调度   | APScheduler                              |

---

## 📁 目录结构

```
yuexia/
├── src/
│   ├── backend/             # FastAPI 后端
│   │   ├── app.py           # 应用工厂 + 启动入口
│   │   ├── core/            # 配置 & 日志
│   │   ├── brain/           # AI 核心（引擎、记忆、提示词、会话、日记）
│   │   ├── perception/      # 感知层（TTS、情感音频池）
│   │   ├── api/             # REST 路由 & WebSocket
│   │   └── services/        # 服务层单例
│   └── frontend/            # React SPA
├── config/config.yaml       # 全局配置
├── assets/                  # 提示词模板、情感参考音频
├── data/                    # 运行时数据（会话、ChromaDB、TTS 音频、日记）
├── shared_claude/           # 多 Claude 实例协作上下文
├── .runtime/                # 运行时数据（端口文件、PID 等）
├── GPT-SoVITS-v2-240821/   # TTS 引擎
├── launcher.py              # 启动脚本（推荐）
├── start.bat                # Windows 一键启动
└── docs/                    # 项目文档
```

---

## 📋 已实现功能

### ✅ 核心对话能力

**灵活的推理引擎架构**：支持 vLLM、Transformers、OpenAI API 三种推理模式，自动根据运行环境选择最优方案（Windows 自动降级至 Transformers），同时支持多模态输入（文本 + 图像）和 SSE 流式对话输出，为用户提供流畅的交互体验。

**多模态推理**：支持 Qwen3-VL 视觉理解，能够理解文本和图像输入，为对话提供更丰富的上下文。

**Markdown 渲染**：支持代码块语法高亮、复制按钮、GFM 表格，让对话内容更加丰富和易读。

### ✅ 记忆与日记系统

**长期记忆**：通过 ChromaDB 向量数据库，月下能记住你们的对话历史，并在合适的时候回忆起过去的交流。支持语义检索，能够根据对话内容自动关联历史记录。

**AI 日记生成**：支持日记、周记、月记、年记四种类型，每种类型独立配置（启用开关、频率、提示词），支持立即记录功能。日记以 Markdown 格式保存，方便查看和管理。

**系统提示词模板管理**：从文件加载系统提示词，支持记忆上下文注入，让月下的回复更加符合你的期望。

### ✅ 语音与情感表达

**情感驱动 TTS**：基于 GPT-SoVITS 的情感驱动 TTS 系统，根据情感标签动态选择参考音频，让每句话都带着恰当的情感。支持多种情感标签（开心、悲伤、生气等）。

**情感音频参考池**：通过 meta.yaml 配置，自动扫描情感目录，支持自定义情感音频。

**TTS 播放按钮**：前端聊天面板支持 TTS 播放按钮，点击即可播放语音，支持自动播放和手动播放两种模式。

### ✅ 交互界面

**沉浸式 Live2D 体验**：Live2D 角色以全屏背景形式呈现，聊天面板以毛玻璃浮层形式固定在右侧，营造沉浸式的交互体验。支持锁定/解锁交互，持久化显示状态。

**多会话管理**：支持创建、切换、重命名、删除会话，历史消息持久化，支持 32 位会话 ID，确保会话唯一性。

**配置管理页面**：Bento Grid 布局，137 个配置项全覆盖，支持热重载。配置项分为 11 个分类（server、brain、behavior、perception.tts、perception.asr、general、session、memory、security、network、diary），每个配置项都有详细的说明。

**实时日志系统**：WebSocket 日志流、过滤、搜索、下载，5000 条缓冲。支持按级别（DEBUG、INFO、WARNING、ERROR）和模块过滤，方便开发者调试。

**系统状态监控**：GPU/VRAM/CPU/内存/推理速度，3 秒轮询，实时显示系统资源使用情况。

**Toast 通知系统**：配置保存、操作反馈，提供友好的用户体验。

**滚动揭示动画和微交互**：配置页面支持滚动揭示动画（Reveal on Scroll）和微交互（Interactive Hover），提升用户体验。

### ✅ 自主行为引擎

**多种触发模式**：支持定时触发（interval）、无输入超时触发（idle）、cron 表达式触发，让月下能够主动与你互动。

**安静时段和每日消息限制**：支持设置安静时段（如工作时间、睡眠时间），让她在合适的时候出现，不会打扰你的生活。每日消息限制功能确保她不会过于频繁地打扰你。

**LLM 生成消息**：优先使用 LLM 生成主动消息（30 秒超时），回退到分类模板选择，确保消息的多样性和自然性。

### ✅ 基础设施

**YAML 全局配置**：137 个配置项，11 个分类，点分路径取值，热更新。配置文件支持环境变量（YUEXIA_ROOT），方便部署和测试。

**配置白名单机制**：约 90 项可前端修改，防止危险配置被篡改，确保系统安全。

**统一日志系统**：WebSocket 广播 + 5000 条缓冲回放，stdout/stderr 重定向，TTS 日志 tail。日志按运行次数分文件夹存储，自动清理（保留最近 5 次）。

**服务层单例管理**：BrainService、PerceptionService、LogService，确保服务的唯一性和稳定性。

**配置变更后服务热重载**：reload_services，引擎锁保护，GPU 显存释放，确保配置变更后服务能够正确重启。

**OpenAPI 3.0 规范 + Swagger UI 文档**：所有 API 端点都有详细的文档，方便开发者集成和扩展。

**Windows 一键启动/停止脚本**：launcher.py + start.bat，环境变量传递，健康检查，确保服务能够正确启动和停止。

**输入校验与错误处理**：长度限制、空值检查、404/503 友好 JSON 响应，确保系统的稳定性和安全性。

**会话数据并发保护**：threading.RLock + 原子写入，确保会话数据的一致性。

**TTS 连接池复用**：httpx.AsyncClient 持久化，减少连接开销，提升 TTS 合成速度。

**Zustand 状态管理**：WebSocket 单例、系统状态缓存、配置 Store、聊天 Store，确保前端状态的一致性和可维护性。

---

## 🔌 API 端点

### REST API

| 端点                           | 方法           | 说明             |
| ---------------------------- | ------------ | -------------- |
| `/api/chat/stream`           | POST         | SSE 流式聊天       |
| `/api/sessions`              | GET / POST   | 会话列表 / 创建      |
| `/api/sessions/<sid>`        | GET / DELETE | 加载 / 删除会话      |
| `/api/sessions/<sid>/switch` | POST         | 切换会话           |
| `/api/sessions/<sid>/rename` | PUT          | 重命名会话          |
| `/api/config`                | GET / PUT    | 读取 / 更新配置      |
| `/api/diary/immediate`       | POST         | 立即生成日记（所有启用类型） |
| `/api/system/status`         | GET          | 系统资源状态         |
| `/api/screenshot`            | GET          | 屏幕截图           |
| `/api/emotion-refs`          | GET          | 情感参考音频列表       |
| `/api/asr/devices/input`     | GET          | 音频输入设备列表       |
| `/api/asr/devices/output`    | GET          | 音频输出设备列表       |
| `/api/asr/test/start`        | POST         | 开始麦克风测试        |
| `/api/asr/test/stop`         | POST         | 停止麦克风测试        |
| `/api/docs`                  | GET          | Swagger UI     |

### WebSocket

| 端点           | 说明                   |
| ------------ | -------------------- |
| `/ws/logs`   | 实时日志流                |
| `/ws/events` | 事件推送（表情、TTS 完成、主动消息） |

### API 调用示例

```python
# SSE 流式聊天
import requests

response = requests.post(
    "http://localhost:5000/api/chat/stream",
    json={"text": "你好，月下"},
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

```python
# 获取系统状态
import requests

response = requests.get("http://localhost:5000/api/system/status")
print(response.json())
```

---

## 📝 TODO

详细的 TODO 列表和版本变更记录请查看 [shared_claude/VERSIONS.md](shared_claude/VERSIONS.md)。

### 🚧 高优先级

- [ ] ASR 语音识别服务集成（API 端点已定义，服务未接入）
- [ ] Live2D 唇形同步（根据音频振幅驱动口型参数）
- [ ] Live2D 表情动画（根据情感标签驱动表情切换）

### 🧪 中优先级

- [ ] 屏幕持续感知（视频流或定时截图输入 Brain）
- [ ] 感知-动作-观察闭环（操作后截图反馈至 Brain）
- [ ] 浏览器自动化（Playwright 集成）

### 💡 低优先级

- [ ] MCP 工具宿主（Model Context Protocol Server）
- [ ] LoRA 微调 Pipeline（nightly_finetune.py）

---

## 📄 许可证

MIT License

---

## 🙏 致谢

训练数据来源：B站UP主：[MC神神希](https://space.bilibili.com/666904408)

live2d来源：B站up主：[支线路人A](https://space.bilibili.com/1152374880)