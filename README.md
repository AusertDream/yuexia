# 月下 (YueXia)

本地部署的 AI 虚拟伴侣，具备多模态对话、语音合成、情感表达、长期记忆与日记能力。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + TypeScript + Vite 6 + TailwindCSS 4 |
| 后端 | Flask + Flask-SocketIO |
| LLM | Qwen3-VL-4B-Instruct（vLLM / Transformers 双模） |
| TTS | GPT-SoVITS v2（HTTP API） |
| ASR | Faster-Whisper + Silero-VAD |
| 向量数据库 | ChromaDB |
| Live2D | PixiJS + Cubism 4 SDK |

## 目录结构

```
yuexia/
├── src/
│   ├── backend/             # Flask 后端
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
├── shells/                  # 启动/停止/安装脚本
├── static_frontend/         # UI 设计稿
├── GPT-SoVITS-v2-240821/   # TTS 引擎
└── docs/                    # 项目文档
```

## 已实现功能

### 核心认知层 (Brain)

- [x] vLLM / Transformers 双模推理引擎，自动降级（Windows 自动使用 Transformers）
- [x] 多模态推理（文本 + 图像输入），支持 Qwen3-VL 视觉理解
- [x] SSE 流式对话输出
- [x] ChromaDB 向量记忆，语义检索历史对话（可通过配置开关）
- [x] 系统提示词模板管理（从文件加载，支持记忆上下文注入）
- [x] 多会话管理（创建、切换、重命名、删除、历史消息持久化）
- [x] AI 日记生成（DiaryWriter，LLM 自动总结对话并写入 Markdown）
- [x] 情感标签提取（从 LLM 回复中解析 `[emotion:xxx]` 标签）

### 感知与表达层 (Perception & Expression)

- [x] GPT-SoVITS 情感驱动 TTS（根据情感标签动态选择参考音频）
- [x] 情感音频参考池（EmotionPool，支持 meta.yaml 配置，自动扫描情感目录）
- [x] TTS 合成完成后通过 WebSocket 推送事件，前端自动播放
- [ ] ASR 语音识别服务集成（API 端点已定义，后端服务未接入）
- [ ] 实时麦克风音频采集 + Silero-VAD 语音切分

### 交互层 (Face)

- [x] React Web UI 仪表盘（Dashboard）
- [x] Live2D 角色模型嵌入（PixiJS + Cubism 4 SDK，iframe 渲染）
- [x] 聊天面板（流式输出、多会话标签切换）
- [x] 前端语音输入（Web Speech API）
- [x] 系统状态实时监控（GPU/VRAM/CPU/内存/推理速度，3 秒轮询）
- [x] 配置管理页面（Brain、TTS、ASR、Memory、屏幕截图等全部可配置项）
- [x] 感知监控页面（视觉输入、ASR 文本流、动作输出、服务状态）
- [x] 实时日志页面（WebSocket 日志流、过滤、搜索、下载）
- [x] 侧边栏导航（仪表盘、配置、感知、日志）
- [ ] Live2D 唇形同步（根据音频振幅驱动口型参数）
- [ ] Live2D 表情过渡动画（根据情感标签驱动表情切换）

### 动作层 (Action)

- [x] 屏幕截图 API（`/api/screenshot`，返回 Base64 JPEG）
- [ ] MCP 工具宿主（Model Context Protocol Server）
- [ ] 浏览器自动化（Playwright）
- [ ] 系统级操作（键鼠控制、文件读写）
- [ ] 感知-动作-观察闭环（截图反馈至 Brain 层）

### 基础设施

- [x] YAML 全局配置（点分路径取值，热更新）
- [x] 统一日志系统（WebSocket 广播 + 200 条缓冲回放）
- [x] 服务层单例管理（BrainService、PerceptionService、LogService）
- [x] 后台线程异步启动服务（boot_services）
- [x] 配置变更后服务热重载（reload_services）
- [x] OpenAPI 3.0 规范 + Swagger UI 文档
- [x] Windows 一键启动/停止脚本（start.bat / stop.bat）
- [x] 日志按运行次数分文件夹存储，自动清理（保留最近 5 次）
- [x] 输入校验与错误处理（长度限制、空值检查、404/503 友好 JSON 响应）

### 自进化系统

- [x] AI 日记模块（每次对话后 LLM 自动生成日记，保存为 Markdown）
- [ ] LoRA 微调 Pipeline（nightly_finetune.py）

## API 端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/chat/stream` | POST | SSE 流式聊天 |
| `/api/sessions` | GET / POST | 会话列表 / 创建 |
| `/api/sessions/<sid>` | GET / PUT / DELETE | 切换 / 重命名 / 删除会话 |
| `/api/config` | GET / PUT | 读取 / 更新配置 |
| `/api/system/status` | GET | 系统资源状态 |
| `/api/screenshot` | GET | 屏幕截图 |
| `/api/emotion-refs` | GET | 情感参考音频列表 |
| `/api/asr/devices` | GET | 音频输入设备列表 |
| `/api/docs` | GET | Swagger UI |
| `/ws/logs` | WebSocket | 实时日志流 |
| `/ws/events` | WebSocket | 事件推送（表情、TTS 完成） |

## 启动

```bash
# 一键启动（TTS + Backend + Frontend）
start.vbs

# 或手动分别启动
python -m src.backend.app              # Backend :5000
cd src/frontend && npm run dev         # Frontend :5173
# GPT-SoVITS 需单独启动               # TTS :9880
```

## 未实现功能（按 plan.md 路线图）

| 功能 | 所属层 | 阶段 | 备注 |
|------|--------|------|------|
| ASR 语音识别服务集成 | 感知层 | 第一阶段 | API 端点已定义，服务未接入 |
| Live2D 唇形同步 | 交互层 | 第二阶段 | 需根据音频振幅驱动口型参数 |
| Live2D 表情动画 | 交互层 | 第二阶段 | 需根据情感标签驱动表情切换 |
| MCP 工具宿主 | 动作层 | 第三阶段 | plan 标注"不急，可以先不实现" |
| 浏览器自动化 | 动作层 | 第三阶段 | Playwright 集成 |
| 屏幕持续感知 | 动作层 | 第三阶段 | 视频流或定时截图输入 Brain |
| 感知-动作-观察闭环 | 动作层 | 第三阶段 | 操作后截图反馈至 Brain |
| LoRA 微调 Pipeline | 自进化 | 第四阶段 | plan 标注"先不用做" |
