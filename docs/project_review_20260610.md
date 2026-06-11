# 月下 (YueXia) 项目全面评估报告

> 评估日期：2026-06-10
> 评估方式：全量代码探索（后端 src/backend 全模块、前端 src/frontend 全模块、Live2D 静态页、配置文件、shared_claude 协作记录、git 历史）
> 评估视角：项目全貌梳理 + 功能完成度核实 + 最终用户体验改进建议

---

## 一、这是一个什么项目

**月下是一个完全本地运行的 AI 虚拟伴侣系统**，目标是打造一个"真正属于你"的数字角色：她有 Live2D 视觉形象、带情感的语音、长期记忆、会写日记、还会主动找你聊天。所有数据（对话、记忆、日记、语音）都存在本机，不依赖云端，主打隐私自主。训练数据和 Live2D 模型来自 B 站 UP 主（角色原型为"MC神神希"，Live2D 来自"支线路人A"）。

### 技术架构（三个进程协作）

| 服务 | 技术 | 端口 |
|---|---|---|
| 后端 | FastAPI + Socket.IO (ASGI)，LLM 用 Qwen3-VL-4B-Instruct（Transformers / vLLM / OpenAI API 三模） | 5000 |
| 前端 | React 19 + TypeScript + Vite 6 + TailwindCSS 4 + Zustand，Live2D 用 PixiJS + Cubism 4 | 5173 |
| TTS | GPT-SoVITS v2 独立进程（角色定制音色，HTTP API） | 9880 |

### 后端核心流程

后端核心是 `BrainService` 中枢（`src/backend/services/brain_service.py`）：收到用户消息后依次执行：

```
记忆检索 → 拼装提示词 → LLM 流式生成 → 解析情感标签
→ 持久化会话 → 触发情感 TTS → 推送表情事件 → 检查是否该写日记
```

外围子系统：

- **行为引擎**（`brain/behavior_engine.py`）：APScheduler 驱动，支持 interval / idle / cron 三种主动消息触发器，带安静时段和每日消息上限，优先 LLM 生成消息、回退分类模板。
- **记忆**（`brain/memory.py`）：ChromaDB 向量库，对话写入 + 语义检索。
- **日记**（`brain/diary.py`）：日/周/月/年四类日记，LLM 生成 Markdown 落盘到 `data/diary/`。
- **ASR**（`perception/asr.py`，v0.9.5 进行中）：Faster-Whisper + Silero-VAD，支持文件转写和实时麦克风识别。
- **情感 TTS**（`perception/tts.py` + `emotion_pool.py`）：按情感标签从 `assets/emotion_refs/` 选取参考音频，调 GPT-SoVITS 合成。
- **日志服务**（`services/log_service.py`）：WebSocket 实时广播 + JSONL 结构化持久化 + TTS 独立进程日志 tail。

### 前端结构

四个页面（`App.tsx` 路由）：

| 路由 | 页面 | 功能 |
|---|---|---|
| `/` | DashboardPage | Live2D 全屏背景 + 毛玻璃聊天浮层（会话标签、SSE 流式、TTS 播放、麦克风按钮） |
| `/config` | ConfigPage | Bento Grid 布局的配置中心（主题、LLM、行为引擎、TTS、ASR、记忆、日记等 137 项） |
| `/perception` | PerceptionPage | 视觉截图轮询、ASR 文字流、表情事件日志 |
| `/logs` | LogsPage | 终端风格实时日志（级别过滤、搜索、导出） |

状态管理为 4 个 Zustand store：`useSocketStore`（WebSocket 单例，events + logs 双连接）、`useChatStore`（会话/消息/主动消息/TTS 路径）、`useConfigStore`（配置 + 主题即时应用）、`useSystemStore`（系统状态引用计数轮询）。

### 项目成熟度

从 git 历史和 shared_claude 协作记录看，项目工程化程度远超同类个人项目：

- 经历 Qt 桌面应用 → Flask → FastAPI 两次大重构；
- 走完"止血 → 加固 → 增强 → 演进"四阶段改进路线图（v0.5.0 → v0.8.0）；
- 做过 77 项问题的全量代码审查、29/29 通过的端到端测试、多轮验收测试；
- 具备 137 项配置、约 90 项白名单防护、会话 RLock 并发保护、原子写入、TTS 连接池、统一日志等工程细节；
- 多 Claude 实例通过 shared_claude 目录协作，维护 PROJECT/STATUS/VERSIONS 三份文档。

当前未提交的改动是正在进行中的 ASR 语音输入集成（v0.9.5：`perception/asr.py` 新文件 + asr_api 扩展 + ChatPanel 麦克风按钮）。

---

## 二、各功能真实完成度（代码验证后的结论）

| 功能 | 状态 | 说明 |
|---|---|---|
| 文本对话（SSE 流式 + 多模态） | ✅ 完整 | 主链路最扎实的部分，含历史裁剪、情感标签解析、会话持久化 |
| 情感 TTS | ✅ 基本完整 | 情感参考音频池工作正常；但配置里的 `retry_count`/`retry_delay` 没有真正实现，无服务探活 |
| 会话管理 | ✅ 完整 | 增删改查、原子写入、十六进制 sid 防路径遍历、删除时级联清理 TTS 音频 |
| 主动消息 | ✅ 已闭环 | 后端 `proactive_message` 事件 → `useSocketStore` 全局监听 → `useChatStore.handleProactiveMessage` 进入聊天流 |
| 日志/状态监控 | ✅ 完整 | WebSocket 日志流 + 系统资源轮询 + Swagger 文档 |
| ASR 语音输入 | 🟡 半成品 | 识别能力完整（文件/实时/设备枚举/麦克风测试），但识别结果只 append 进输入框，仍需手动点发送；`push_to_talk` / `ptt_key` 配置项无对应实现 |
| 长期记忆 | 🟡 默认关闭 | 代码链路接通（检索 + 写入 + 提示词注入），但 `memory.enabled: false`，且 chromadb 未装时静默禁用，用户感受不到"她记得我" |
| 日记 | 🟡 行为不可预期 | 只在"每轮聊天后顺便检查"时生成，不是定时任务；`diary.frequency`/`auto_generate` 配置不具备真实调度语义；**前端没有任何查看日记的页面** |
| Live2D 表情/口型 | ❌ 断链 | 管线两端都已实现但中间没接上（详见下文第一优先项） |
| 浏览器/屏幕操作（"四肢"） | ❌ 仅配置占位 | `action.browser.*`、`face.*` 等配置存在但无任何实现 |

---

## 三、从用户角度的改进建议（按影响排序）

### 🔴 第一优先：把 Live2D 从"壁纸"变成"活人"

这是产品定位（虚拟伴侣）和现状落差最大的地方。目前 Live2D 是 `DashboardPage → LivePreview → iframe(/live2d/index.html)` 嵌入的静态页面，与 React 应用完全隔离，只有呼吸和摆动的待机动画。代码核实结论：

- `src/frontend/public/live2d/app.js:119` 的 `playAudio()` 带口型同步逻辑（驱动 `ParamMouthOpenY`），**但是死代码**——iframe 内没有 socket 连接，父页面 postMessage 只传 `set-lock` 锁定状态，没有任何调用方。
- React 端 `ChatPanel.playTts()` 用自己独立的 `new Audio()` 播放 TTS，与角色完全无关。
- 后端每轮对话都解析情感标签并推送 `expression` 事件，但前端只在 PerceptionPage 把它当文字记日志，**从未驱动模型表情**。

**改进路径**：把 TTS 播放收敛到一处，通过 postMessage 把音频路径和情感标签传进 iframe，激活已有的口型代码，并把情感标签映射到 Live2D 表情参数。这是全项目投入产出比最高的一项——用户立刻能感觉到"她在对我说话"，而不是"喇叭在响，立绘在发呆"。顺带可把假口型（正弦波模拟）升级为 Web Audio API（AnalyserNode）的真实振幅分析。

### 🔴 第二优先：打通"免提语音对话"闭环

现在的语音体验是：点麦克风 → 说话 → 文字出现在输入框 → **手动点发送** → 等回复 → 回复有声音。对一个"伴侣"产品，用户期望的是说完话她直接回应。

**改进路径**：加一个"对话模式"开关——VAD 检测到句子结束后自动发送，回复完成后 TTS 自动播放，形成 说 → 听 → 说 的连续循环。后端 ASR/VAD/静音切分能力都已就绪（`perception/asr.py` 已有句子完整性保护），缺的只是前端 `onAsrResult` 回调里从"填输入框"改为"可选自动发送"这一步。

### 🟠 第三优先：默认开启记忆，并让"被记住"可感知

"她能记住你们的每一次交流"是 README 第一句卖点，但 `memory.enabled: false`，开箱体验里这个核心卖点不存在。

**改进路径**：
1. 解决 chromadb 依赖安装问题（写入 requirements 并在安装脚本中验证），默认开启记忆；
2. 在 UI 上做轻量呈现——回复中引用了历史记忆时给个小标记（如"她想起了 3 月那次对话"），让记忆从纯后台机制变成可感知的情感价值；
3. 补全 `memory.embedding_model`、`auto_persist` 等配置项的真实消费逻辑（当前只依赖 Chroma 默认行为）。

### 🟠 第四优先：给日记一个家

日记是这个产品最有"人格温度"的功能——但它生成后只是躺在 `data/diary/*.md` 里，前端四个页面没有任何入口能看到。README 说"你可以随时查看她的内心世界"，实际上普通用户根本找不到。

**改进路径**：
1. 新增日记页面（按日/周/月/年分栏，Markdown 渲染，时间线浏览），相对独立、容易实现；
2. 把日记触发从"聊天后顺便检查"改成真正的定时调度——行为引擎里现成的 APScheduler 可直接复用，让 `diary.frequency` / `generation_time` 配置变成真的；否则"今天写了明天没写"的行为用户无法理解。

### 🟡 第五优先：安装体验（决定有没有"第一个用户"）

内部验收已发现此问题（V5 项：新用户首次安装成功率约 0%）：模型路径硬编码 `E:\models\...`、install.bat 未安装 CUDA 版 PyTorch、GPT-SoVITS 无安装步骤、conda activate 静默失败、前置条件未文档化。

**改进路径**：只要目标包含"给别人用"，建议做引导式首次启动——检测依赖 → 提示模型下载位置 → 在配置页填模型路径（而不是手改 YAML）→ 各服务健康检查给出具体的失败原因和修复指引。

### 🟡 其余值得收拾的点

1. **配置项虚胖**：137 项配置中相当一部分是"摆设"，无对应实现：`perception.tts.retry_count/retry_delay`、`perception.asr.push_to_talk/ptt_key`、`diary.frequency/auto_generate`、`memory.auto_persist`、`action.browser.*`、`face.*`、部分 `network.*`。用户改了没效果会以为软件坏了。建议要么实现、要么从配置页隐藏，保持"看到的都是真的"。

2. **MarkdownRenderer 不渲染**的遗留 bug（react-markdown v10 与 React 19 / TailwindCSS 4 兼容性，见 STATUS.md 已知问题）仍在 TODO，影响日常阅读体验。

3. **错误恢复偏硬**：
   - 引擎加载失败直接 `sys.exit(1)`，无降级路径；
   - TTS 服务没启动时用户只看到失败，没有"请先启动 GPT-SoVITS"的引导；
   - 对话产品宁可降级（无语音继续聊）也不应整体罢工。

4. **配置保存触发全量服务重载**（`reload_services()` 含 LLM 引擎关闭/重建、GPU 显存释放），改个主题色也可能引发服务中断。建议按配置类别区分是否需要重载（UI 类配置免重载、引擎类配置才重载）。

5. **TTS emoji 处理**：GPT-SoVITS 端 GBK 编码问题，当前靠清理 emoji 规避，长期建议在 TTS 端设置 UTF-8。

6. **安全默认值**：`security.api_access_control: false`，请求大小限制和 rate limit 默认不生效；本机使用无碍，若暴露到局域网需提醒用户开启。

---

## 四、代码层面风险点（不影响日常使用，重构时留意）

1. **`BrainService` 自建 event loop 线程**（`asyncio.new_event_loop()` + `run_forever()`），缺少完整统一的停循环/关线程流程，退出和热重载时可能有悬挂任务。

2. **多处跨线程调度依赖同一个 loop**（`asyncio.run_coroutine_threadsafe`）：主动消息、TTS 完成回写、实时 ASR 推送都走这条路，loop 状态异常时表现为静默失败，只在日志留痕，是主动消息/TTS 偶发丢失的高危区。

3. **行为引擎 LLM 消息生成阻塞**：`BehaviorEngine._generate_llm_message()` 用 `future.result(timeout=30)` 阻塞 scheduler 线程，引擎忙时可能卡住后续触发。

4. **`api/ws.py` 是空壳**：WebSocket 实现已迁移到 `app.py` 的 Socket.IO，残留文件易误导维护者，建议删除或合并说明。

5. **代码审查遗留项**（见 STATUS.md）：C1 类型注解、C3 `_inferring` 线程安全注释、M2 历史裁剪硬编码阈值、M3 config.get 哨兵值、M6 API 层 sid 前置校验、M7 tts `_sync_close` 事件循环冲突，以及约 14 个 P2 问题。

---

## 五、一句话总结

这个项目的**工程底盘已经远超同类个人项目**（架构、测试、日志、协作流程都很规范），当前的瓶颈不在代码质量，而在**体验闭环**：四条核心管线（表情、口型、语音输入、记忆/日记）每条都修到了 80%，但都差最后 20% 没接到用户眼前。优先把 Live2D 联动和免提语音这两条接通，产品就能从"功能演示"跨到"真的像个伴侣"。
