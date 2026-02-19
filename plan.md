# AI 二次元数字人项目详细开发路线与技术规格 

## 1. 全局系统架构 (System Overview)

本项目采用**微服务化解耦架构**，强调本地化高性能运行。全系统由四个核心逻辑层组成，各层通过定义的 `YueXiaProtocol` (基于 Pydantic) 进行数据交换。

- **交互层 (Face Layer)**: 负责视觉呈现、UI 交互及音视频流的端点处理。
- **感知与表达层 (Perception & Expression Layer)**: 负责 ASR 语音识别与带情感驱动的 TTS 合成。
- **核心认知层 (Brain Layer)**: 本地多模态 LLM 核心，负责决策、对话、视觉理解及记忆检索。
- **动作层 (Action Layer)**: 负责驱动 MCP 工具调用、系统级操作及浏览器自动化。

## 2. 模块详细开发规格

### 2.1 交互层 (Face Layer)

**技术栈**: `PySide6`, `QWebEngineView`, `PixiJS (Live2D)`, `Three.js (VRM)`.

- **开发任务**:
  1. **透明容器**: 构建基于 PySide6 的无边框、背景透明窗口，支持跨平台（Windows/Linux）的 GPU 加速。
  2. **渲染桥接**: 通过 `QWebChannel` 实现 Python 与 WebGL 渲染引擎的高频通信，用于同步动作与表情。
  3. **音频与口型**: 播放 `Perception & Expression 层` 生成的音频，并根据振幅实时驱动 Live2D 模型的口型参数。

### 2.2 感知与表达层 (Perception & Expression Layer)

**技术栈**: `Faster-Whisper`, `GPT-SoVITS`, `Librosa`.

- **开发任务**:
  1. **多模态输入处理**: 实时采集麦克风音频，利用 `Silero-VAD` 进行语音切分并交由 `Faster-Whisper` 识别。
  2. **情感驱动 TTS**:
     - 维护一个**情感音频参考池**。
     - 根据 Brain 层下发的 `emotion_tag` 动态选择参考音频，确保音调与语境匹配。
     - 音频输出使用gpt-sovits合成音频。

### 2.3 核心认知层 (Brain Layer)

**技术栈**: `vLLM` (首选), `Transformers` (备选), `ChromaDB`.

- **推理引擎逻辑**:
  1. **优先级加载**:
     - **vLLM 模式**: 系统启动时检测 CUDA 环境与显存。若支持，使用 vLLM 加载模型以获取更高的吞吐量和推理速度。
     - **Transformers 模式**: 若 vLLM 不可用（如缺少特定算子支持或显存极端受限），则降级使用 `transformers` 库加载模型，确保基础运行。
  2. **多模态推理**: 统一处理 `Text + Vision` 输入。接收来自 `Action 层` 的屏幕截图或者视频流，实现实时环境感知。
  3. **Agentic Memory**:
     - 集成 `MemoryTool`。AI 自主判断何时查询 `ChromaDB` 中的历史语料，同时自主判断查询得到的资料是否全部需要。

### 2.4 动作层 (Action Layer)

**技术栈**: `MCP (Model Context Protocol)`, `Playwright`, `PyAutoGUI`.

备注：调用MCP工具不急，可以先不实现。

- **开发任务**:
  1. **MCP 宿主**: 构建符合标准的 MCP Server，用于连接 LLM 与操作系统 API。
  2. **工具集**:
     - **Web 工具**: 自动浏览网页、信息抓取。
     - **系统工具**: 截图、文件读写、键鼠控制（支持游戏/应用操控）。
  3. **反馈循环**: 执行操作后自动截取画面并反馈至 Brain 层，形成“感知-动作-观察”的闭环。

## 3. 内部通信协议规格 (YueXiaProtocol)

以下只是一个示例，根据实际情况设计通信协议。

```
from pydantic import BaseModel, Field
from typing import List, Optional

class ActionSignal(BaseModel):
    motion: str = "idle"         # 动作标识
    expression: str = "neutral"  # 表情标识
    intensity: float = 1.0       # 动作/表情强度

class BrainResponse(BaseModel):
    session_id: str
    text_content: str            # AI 回复文本
    emotion_tag: str             # 情感标签 (happy/angry/sad...)
    action_signals: List[ActionSignal] # 驱动 Face 层的信号
    tools_needed: List[str]      # 驱动 Action 层的工具调用


```

## 4. 实施阶段路线图

### 第一阶段：基础架构 

- **Face**: 实现透明 WebGL 容器与基础 Live2D 模型加载。
- **Perception**: 搭建流式 ASR 系统。
- **Brain**: 实现基于 vLLM/Transformers 的双模加载机制，打通基础对话。

此阶段需要提交可运行的应用成果，能够实现基本的多模态文本聊天，输入语音转文字。

### 第二阶段：情感与记忆

- **Perception**: 完成情感参考池与 TTS 的对接。
- **Brain**: 接入 ChromaDB 向量库，实现“按需检索”记忆。
- **Face**: 实现唇形同步算法与表情过渡动画。

### 第三阶段：能力扩展

- **Action**: 接入 MCP 协议。实现浏览器自动化与屏幕实时感知。
- **Brain**: 优化多模态 Prompt 策略，使 AI 能“看”懂屏幕并进行复杂操作。

此阶段交付AI能够使用基本的MCP工具即可，这里可以浏览器MCP作为验证，其他的MCP工具可以后续添加。另外AI应该能够持续的看屏幕，看的方式可以是输入视频流，或者是每隔一段时间的屏幕截图，两种可选。

### 第四阶段：自进化系统 (持续)

- **Train**: 开发 `nightly_finetune.py`。
- **逻辑**: 自动收集并标注当日对话语料，利用 LoRA 技术进行模型热更新。

这部分先不用做，需要做的只是，让AI以日记的形式，记录每一次对话的内容，总结，以及自己的所感所思所想。其他的自更新pipeline先不用实现。

## 5. 其他注意事项

所有相关产出文件均存放在源文件夹下，需要一个配置文件，用来配置各种可配置项，比如gpt sovits的音频模型，brain的backbone模型路径等等。模型加载均本地加载。

同时考虑到brain层可能需要持续 运行，然后其各模块需要异步调用brain模块来判断，所以需要考虑各模块异步同步等问题，如果是vllm加载，则严禁将vllm放在一个子进程里面，会出问题的。以brain层为主进程，其他为副进程。多线程的处理，同时这里也要注意死锁等多线程并发导致的各种问题，具体就不详细列出来了。