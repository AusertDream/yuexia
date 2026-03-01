import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useConfigStore, useSocketStore } from '../stores'
import SystemStatusCard from '../components/config/SystemStatusCard'
import { useSystemStatus } from '../stores/useSystemStore'
import { toast } from '../stores/useToastStore'

const ACCENT_COLORS = ['#60cdff', '#ff6060', '#60ff8b', '#ffc460', '#c260ff']
const ENGINES = ['transformers', 'vllm', 'api'] as const
const TTS_ENGINES = ['local', 'api'] as const
const EMBEDDING_MODELS = ['text-embedding-3-small', 'm3e-base', 'bge-large-zh'] as const
const ASR_SIZES = ['tiny', 'base', 'small', 'medium', 'large-v3'] as const
const COMPUTE_TYPES = ['float16', 'int8_float16', 'int8'] as const

const EMOTION_COLORS: Record<string, string> = {
  happy: 'bg-yellow-400', angry: 'bg-red-400', sad: 'bg-blue-400', neutral: 'bg-gray-400',
  shy: 'bg-pink-400', excited: 'bg-orange-400', surprised: 'bg-purple-400',
}

const ScrollContainerContext = createContext<HTMLDivElement | null>(null)

export default function ConfigPage() {
  const { config: cfg, loading, loadConfig, saveConfig, updateField, resetConfig } = useConfigStore()
  const [refs, setRefs] = useState<{ emotion: string; file: string }[]>([])
  const [inputDevices, setInputDevices] = useState<{ index: number; name: string }[]>([])
  const [outputDevices, setOutputDevices] = useState<{ index: number; name: string }[]>([])
  const [micLevel, setMicLevel] = useState(-1)
  const [micTesting, setMicTesting] = useState(false)
  const [chatBgUrl, setChatBgUrl] = useState<string | null>(null)
  const [bgUploading, setBgUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [scrollEl, setScrollEl] = useState<HTMLDivElement | null>(null)
  const scrollRef = (node: HTMLDivElement | null) => { if (node) setScrollEl(node) }
  const systemStatus = useSystemStatus()
  const eventsSocket = useSocketStore(s => s.eventsSocket)

  useEffect(() => {
    loadConfig()
    api.get('/emotion-refs').then(r => setRefs(r.data)).catch(() => {})
    api.get('/asr/devices').then(r => setInputDevices(r.data)).catch(() => {})
    api.get('/asr/output-devices').then(r => setOutputDevices(r.data)).catch(() => {})
    api.get('/config/chat-bg').then(r => {
      if (r.data?.exists && r.data.url) setChatBgUrl(r.data.url)
    }).catch(() => {})
  }, [loadConfig])

  // 主题应用
  useEffect(() => {
    if (!cfg) return
    if (cfg.general?.accent_color) document.documentElement.style.setProperty('--accent-blue', cfg.general.accent_color)
    document.documentElement.classList.toggle('light', !(cfg.general?.dark_mode ?? true))
    if (cfg.general?.font_size) document.documentElement.style.setProperty('--font-size', `${cfg.general.font_size}px`)
    if (cfg.general?.sidebar_width) document.documentElement.style.setProperty('--sidebar-width', `${cfg.general.sidebar_width}px`)
    document.documentElement.style.setProperty('--transition-duration', cfg.general?.animation_enabled === false ? '0s' : '0.2s')
  }, [cfg?.general?.accent_color, cfg?.general?.dark_mode, cfg?.general?.font_size, cfg?.general?.sidebar_width, cfg?.general?.animation_enabled])

  useEffect(() => {
    return () => { eventsSocket?.off('mic_level') }
  }, [eventsSocket])

  const save = async () => {
    const ok = await saveConfig()
    if (ok) toast.success('配置已保存')
    else toast.error('保存失败')
  }

  const handleImmediateDiary = async () => {
    try {
      const response = await api.post('/diary/immediate')
      const data = response.data
      if (response.status === 200) {
        toast.success('日记生成成功')
      } else {
        toast.error(data.error || '日记生成失败')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.error || '请求失败')
    }
  }

  const startMicTest = () => {
    if (!eventsSocket) return
    const device = cfg?.perception?.asr?.mic_device ?? null
    setMicTesting(true)
    setMicLevel(0)
    eventsSocket.off('mic_level')
    eventsSocket.on('mic_level', (d: { level: number }) => {
      if (d.level < 0) { setMicTesting(false); setMicLevel(-1); eventsSocket.off('mic_level'); return }
      setMicLevel(d.level)
    })
    api.post('/asr/mic-test', { device }).catch(() => { setMicTesting(false); eventsSocket.off('mic_level') })
  }

  const stopMicTest = () => {
    setMicTesting(false)
    setMicLevel(-1)
    eventsSocket?.off('mic_level')
    api.post('/asr/mic-test-stop').catch(() => {})
  }

  const uploadBg = async (file: File) => {
    setBgUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const r = await api.post('/config/chat-bg', form)
      const url = r.data?.url || null
      setChatBgUrl(url)
      window.dispatchEvent(new CustomEvent('chat-bg-changed', { detail: { url } }))
      toast.success('背景已更新')
    } catch {
      toast.error('背景上传失败')
    } finally {
      setBgUploading(false)
    }
  }

  const resetBg = async () => {
    try {
      await api.delete('/config/chat-bg')
      setChatBgUrl(null)
      window.dispatchEvent(new CustomEvent('chat-bg-changed', { detail: { url: null } }))
      toast.success('已恢复默认背景')
    } catch {
      toast.error('重置背景失败')
    }
  }

  if (loading || !cfg) return <div className="p-6 text-gray-400">Loading...</div>

  return (
    <ScrollContainerContext.Provider value={scrollEl}>
    <div ref={scrollRef} className="p-6 h-full overflow-y-auto custom-scrollbar flex flex-col gap-6">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white">系统配置</h1>
          <p className="text-xs text-gray-500 mt-1">配置外观、核心 AI 大脑、感知模型和记忆向量。</p>
        </div>
        <div className="flex gap-3">
          <button onClick={resetConfig} className="glass-panel interactive-hover px-4 py-2 text-sm font-medium flex items-center gap-2 text-white rounded-lg hover:bg-white/10">
            <span className="material-symbols-outlined text-[18px]">restart_alt</span>重置
          </button>
          <button onClick={save} className="px-5 py-2 bg-[var(--accent-blue)] text-black text-sm font-medium rounded-lg hover:bg-cyan-300 flex items-center gap-2 shadow-[0_0_15px_rgba(96,205,255,0.3)] interactive-hover">
            <span className="material-symbols-outlined text-[18px]">save</span>
            保存配置
          </button>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-5">
        {/* System Status - full width banner */}
        <Section title="系统监控" icon="monitoring" desc="实时硬件与服务状态" className="col-span-12" delay={0}>
          <SystemStatusCard status={systemStatus} />
        </Section>
        {/* 通用设置 - full width */}
        <Section title="通用设置" icon="tune" desc="应用外观与主题偏好" className="col-span-12" delay={0}>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 bg-black/20 rounded-lg border border-white/5">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-gray-400">dark_mode</span>
                <div><div className="text-sm font-medium">深色模式</div><div className="text-xs text-gray-500">启用全局深色主题</div></div>
              </div>
              <div className="flex items-center">
                <Toggle checked={cfg.general?.dark_mode ?? true} onChange={v => updateField('general.dark_mode', v)} />
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-black/20 rounded-lg border border-white/5">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-gray-400">palette</span>
                <div><div className="text-sm font-medium">主题色</div><div className="text-xs text-gray-500">选择系统高亮颜色</div></div>
              </div>
              <div className="flex gap-2">
                {ACCENT_COLORS.map(c => (
                  <div key={c} onClick={() => updateField('general.accent_color', c)}
                    className={`w-6 h-6 rounded-full cursor-pointer border-2 transition-all hover:scale-110 ${cfg.general?.accent_color === c ? 'border-white shadow-[0_0_0_2px_rgba(255,255,255,0.2)]' : 'border-transparent'}`}
                    style={{ backgroundColor: c }} />
                ))}
              </div>
            </div>
          </div>
          {/* 聊天背景 */}
          <div className="mt-4 pt-4 border-t border-white/5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-gray-400">wallpaper</span>
                <div><div className="text-sm font-medium">聊天背景</div><div className="text-xs text-gray-500">自定义主界面背景图片</div></div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={bgUploading}
                  className="px-3 py-1.5 text-xs font-medium rounded bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/30 transition-colors disabled:opacity-50"
                >
                  {bgUploading ? '上传中...' : '选择图片'}
                </button>
                {chatBgUrl && (
                  <button
                    onClick={resetBg}
                    className="px-3 py-1.5 text-xs font-medium rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                  >
                    恢复默认
                  </button>
                )}
              </div>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) uploadBg(f)
                e.target.value = ''
              }}
            />
            {chatBgUrl && (
              <div className="relative rounded-lg overflow-hidden border border-white/10 h-24">
                <img src={chatBgUrl} alt="当前背景" className="w-full h-full object-cover" />
                <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                  <span className="text-xs text-white/70">当前背景预览</span>
                </div>
              </div>
            )}
            {!chatBgUrl && (
              <div className="rounded-lg border border-dashed border-white/10 h-24 flex items-center justify-center">
                <span className="text-xs text-gray-500">使用默认极光渐变背景</span>
              </div>
            )}
          </div>
        </Section>

        {/* 核心认知 - 8 cols */}
        <Section title="核心认知 (Brain Layer)" icon="psychology" desc="管理 LLM 推理引擎和模型权重" className="col-span-8" delay={0}>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-2">推理后端</label>
                  <div className="flex p-1 bg-black/30 rounded-lg border border-white/5">
                    {ENGINES.map(e => (
                      <button key={e} onClick={() => updateField('brain.engine', e)}
                        className={`flex-1 py-2 text-xs font-medium rounded transition-colors ${cfg.brain?.engine === e ? 'bg-white/10 shadow text-white border border-white/10' : 'text-gray-500 hover:text-white'}`}>
                        {e === 'vllm' ? 'vLLM (CUDA)' : e === 'transformers' ? 'Transformers' : 'API 调用'}
                      </button>
                    ))}
                  </div>
                </div>
                {cfg.brain?.engine === 'api' ? (
                  <>
                    <Field label="API 地址">
                      <input className="input-field" value={cfg.brain?.api_url || ''} placeholder="https://api.openai.com" onChange={e => updateField('brain.api_url', e.target.value)} />
                    </Field>
                    <Field label="API Key">
                      <input className="input-field" type="password" value={cfg.brain?.api_key || ''} onChange={e => updateField('brain.api_key', e.target.value)} />
                    </Field>
                    <Field label="模型名称">
                      <input className="input-field" value={cfg.brain?.api_model || ''} placeholder="gpt-4o" onChange={e => updateField('brain.api_model', e.target.value)} />
                    </Field>
                  </>
                ) : (
                  <>
                    <Field label="本地模型路径">
                      <input className="input-field" value={cfg.brain?.model_path || ''} onChange={e => updateField('brain.model_path', e.target.value)} />
                    </Field>
                    <div className="flex items-center justify-between py-2 border-b border-white/5">
                      <div><div className="text-sm">GPU 显存占用</div><div className="text-xs text-gray-500">限制 VRAM 使用 (0.1 - 0.95)</div></div>
                      <input type="number" step={0.05} className="input-field w-20 text-center text-sm" value={cfg.brain?.gpu_memory_utilization ?? 0.85} onChange={e => updateField('brain.gpu_memory_utilization', +e.target.value)} />
                    </div>
                  </>
                )}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">启用思考</div>
                  </div>
                  <div className="flex items-center">
                    <Toggle checked={cfg.brain?.enable_thinking ?? false} onChange={v => updateField('brain.enable_thinking', v)} />
                  </div>
                </div>
              </div>
              <div className="bg-black/20 p-5 rounded-lg border border-white/5 space-y-4">
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">生成参数</h4>
                <SliderField label="Temperature" value={cfg.brain?.temperature ?? 0.7} min={0} max={2} step={0.1} onChange={v => updateField('brain.temperature', v)} />
                <SliderField label="Top_P" value={cfg.brain?.top_p ?? 0.9} min={0} max={1} step={0.05} onChange={v => updateField('brain.top_p', v)} />
                <SliderField label="最大 Tokens" value={cfg.brain?.max_tokens ?? 4096} min={512} max={8192} step={512} onChange={v => updateField('brain.max_tokens', v)} />
                <SliderField label="上下文长度" value={cfg.brain?.context_length ?? 8192} min={2048} max={32768} step={1024} onChange={v => updateField('brain.context_length', v)} fmt={v => v >= 1024 ? `${Math.round(v/1024)}k` : String(v)} />
                <SliderField label="Repetition Penalty" value={cfg.brain?.repetition_penalty ?? 1.0} min={1} max={2} step={0.05} onChange={v => updateField('brain.repetition_penalty', v)} />
                <SliderField label="Frequency Penalty" value={cfg.brain?.frequency_penalty ?? 0} min={-2} max={2} step={0.1} onChange={v => updateField('brain.frequency_penalty', v)} />
                <SliderField label="Presence Penalty" value={cfg.brain?.presence_penalty ?? 0} min={-2} max={2} step={0.1} onChange={v => updateField('brain.presence_penalty', v)} />
                <SliderField label="Top_K" value={cfg.brain?.top_k ?? 50} min={1} max={200} step={1} onChange={v => updateField('brain.top_k', v)} />
                <SliderField label="Min_P" value={cfg.brain?.min_p ?? 0} min={0} max={1} step={0.05} onChange={v => updateField('brain.min_p', v)} />
              </div>
            </div>
          </Section>

        {/* 行为引擎 - 4 cols */}
        <Section title="行为引擎" icon="smart_toy" desc="主动消息推送配置" className="col-span-4" delay={0.1}>
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="text-sm">启用行为引擎</div>
                <div className="text-xs text-gray-500">定时推送主动消息</div>
              </div>
              <div className="flex items-center">
                <Toggle checked={cfg.behavior?.enabled ?? false} onChange={v => updateField('behavior.enabled', v)} />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">触发类型</span>
              <select className="input-field w-32 py-1 text-xs" value={cfg.behavior?.trigger_type || 'interval'} onChange={e => updateField('behavior.trigger_type', e.target.value)}>
                <option value="interval">定时</option>
                <option value="idle">无输入</option>
                <option value="cron">Cron</option>
              </select>
            </div>
            <SliderField label="定时间隔 (分钟)" value={cfg.behavior?.interval_minutes ?? 30} min={1} max={120} step={1} onChange={v => updateField('behavior.interval_minutes', v)} />
            <SliderField label="无输入等待 (分钟)" value={cfg.behavior?.idle_timeout_minutes ?? 10} min={1} max={60} step={1} onChange={v => updateField('behavior.idle_timeout_minutes', v)} />
            <SliderField label="每日最大消息数" value={cfg.behavior?.max_daily_messages ?? 50} min={1} max={200} step={1} onChange={v => updateField('behavior.max_daily_messages', v)} />
            <div className="flex items-center justify-between">
              <span className="text-sm">模板消息</span>
              <div className="flex items-center">
                <Toggle checked={cfg.behavior?.message_templates_enabled ?? true} onChange={v => updateField('behavior.message_templates_enabled', v)} />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">LLM 生成</span>
              <div className="flex items-center">
                <Toggle checked={cfg.behavior?.llm_generation_enabled ?? false} onChange={v => updateField('behavior.llm_generation_enabled', v)} />
              </div>
            </div>
          </div>
        </Section>
        {/* TTS - 6 cols */}
        <Section title="语音合成 (TTS)" icon="record_voice_over" desc="" className="col-span-6" delay={0}>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-500 mb-2">TTS 模式</label>
              <div className="flex p-1 bg-black/30 rounded-lg border border-white/5">
                {TTS_ENGINES.map(e => (
                  <button key={e} onClick={() => updateField('perception.tts.engine', e)}
                    className={`flex-1 py-2 text-xs font-medium rounded transition-colors ${(cfg.perception?.tts?.engine || 'local') === e ? 'bg-white/10 shadow text-white border border-white/10' : 'text-gray-500 hover:text-white'}`}>
                    {e === 'local' ? '本地模型' : 'API 调用'}
                  </button>
                ))}
              </div>
            </div>
            {(cfg.perception?.tts?.engine || 'local') === 'local' ? (
              <>
                <Field label="SoVITS Weights (.pth)">
                  <input className="input-field font-mono text-xs" value={cfg.perception?.tts?.sovits_weights || cfg.perception?.tts?.model_path || ''} onChange={e => updateField('perception.tts.sovits_weights', e.target.value)} />
                </Field>
                <Field label="GPT Weights (.ckpt)">
                  <input className="input-field font-mono text-xs" value={cfg.perception?.tts?.gpt_weights || ''} onChange={e => updateField('perception.tts.gpt_weights', e.target.value)} />
                </Field>
                <SliderField label="语速" value={cfg.perception?.tts?.speed ?? 1.0} min={0.5} max={2} step={0.1} onChange={v => updateField('perception.tts.speed', v)} />
                <SliderField label="音量" value={cfg.perception?.tts?.volume ?? 1.0} min={0} max={2} step={0.1} onChange={v => updateField('perception.tts.volume', v)} />
                <SliderField label="情感强度" value={cfg.perception?.tts?.emotion_intensity ?? 1.0} min={0} max={2} step={0.1} onChange={v => updateField('perception.tts.emotion_intensity', v)} />
              </>
            ) : (
              <>
                <Field label="API 地址">
                  <input className="input-field" value={cfg.perception?.tts?.api_url || ''} onChange={e => updateField('perception.tts.api_url', e.target.value)} />
                </Field>
                <Field label="API Key">
                  <input className="input-field" type="password" value={cfg.perception?.tts?.api_key || ''} onChange={e => updateField('perception.tts.api_key', e.target.value)} />
                </Field>
              </>
            )}
            <SliderField label="合成超时 (秒)" value={cfg.perception?.tts?.timeout ?? 30} min={5} max={120} step={5} onChange={v => updateField('perception.tts.timeout', v)} />
            <div className="border-t border-white/5 pt-3">
              <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">参考音频映射</label>
              <div className="space-y-2 mt-2 max-h-[180px] overflow-y-auto pr-1">
                {refs.map((r, i) => (
                  <div key={i} className="group bg-black/20 p-2 rounded border border-white/5 hover:border-white/15 flex items-center justify-between transition-colors">
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${EMOTION_COLORS[r.emotion] || 'bg-gray-400'}`} />
                      <span className="text-xs font-medium capitalize">{r.emotion}</span>
                    </div>
                    <span className="text-[10px] font-mono text-gray-500">{r.file}</span>
                  </div>
                ))}
                {refs.length === 0 && <div className="text-xs text-gray-500">未配置参考音频</div>}
              </div>
            </div>
          </div>
        </Section>

        {/* ASR - 6 cols */}
        <Section title="语音识别 (ASR)" icon="mic" desc="" className="col-span-6" delay={0.1}>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">模型大小</span>
              <select className="input-field w-32 py-1 text-xs" value={cfg.perception?.asr?.model_size || 'medium'} onChange={e => updateField('perception.asr.model_size', e.target.value)}>
                {ASR_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">计算精度</span>
              <select className="input-field w-32 py-1 text-xs" value={cfg.perception?.asr?.compute_type || 'int8'} onChange={e => updateField('perception.asr.compute_type', e.target.value)}>
                {COMPUTE_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <SliderField label="VAD 灵敏度" value={cfg.perception?.asr?.vad_threshold ?? 0.2} min={0} max={1} step={0.1} onChange={v => updateField('perception.asr.vad_threshold', v)} />
            <div className="flex items-center justify-between">
              <span className="text-sm">输入设备</span>
              <select className="input-field w-48 py-1 text-xs" value={cfg.perception?.asr?.mic_device ?? ''} onChange={e => updateField('perception.asr.mic_device', e.target.value === '' ? null : +e.target.value)}>
                <option value="">默认</option>
                {inputDevices.map(d => <option key={d.index} value={d.index}>{d.name}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">输出设备</span>
              <select className="input-field w-48 py-1 text-xs" value={cfg.perception?.tts?.output_device ?? ''} onChange={e => updateField('perception.tts.output_device', e.target.value === '' ? null : +e.target.value)}>
                <option value="">默认</option>
                {outputDevices.map(d => <option key={d.index} value={d.index}>{d.name}</option>)}
              </select>
            </div>
            <div className="border-t border-white/5 pt-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">麦克风测试</span>
                <button onClick={micTesting ? stopMicTest : startMicTest}
                  className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${micTesting ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/30'}`}>
                  {micTesting ? '停止测试' : '开始测试'}
                </button>
              </div>
              {micTesting && (
                <div className="h-3 bg-black/30 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-100"
                    style={{ width: `${micLevel}%`, background: micLevel < 40 ? '#22c55e' : micLevel < 70 ? '#eab308' : '#ef4444' }} />
                </div>
              )}
            </div>
            <div className="flex gap-2 items-center p-2 bg-yellow-900/20 border border-yellow-700/30 rounded text-yellow-200/80 text-xs">
              <span className="material-symbols-outlined text-sm">warning</span>
              已启用 Faster-Whisper 加速推理。
            </div>
          </div>
        </Section>

        {/* 长期记忆 - 6 cols */}
        <Section title="长期记忆 (ChromaDB)" icon="database" desc="" className="col-span-6" delay={0}>
            <div className="grid grid-cols-2 gap-4">
              <Field label="集合名称">
                <input className="input-field" value={cfg.memory?.collection_name || ''} onChange={e => updateField('memory.collection_name', e.target.value)} />
              </Field>
              <Field label="嵌入模型">
                <select className="input-field" value={cfg.memory?.embedding_model || 'm3e-base'} onChange={e => updateField('memory.embedding_model', e.target.value)}>
                  {EMBEDDING_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </Field>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="flex items-center">
                  <Toggle checked={cfg.memory?.auto_persist ?? true} onChange={v => updateField('memory.auto_persist', v)} />
                </div>
                <span className="text-sm">自动持久化</span>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <div className="flex items-center">
                  <Toggle checked={cfg.memory?.enabled ?? false} onChange={v => updateField('memory.enabled', v)} />
                </div>
                <span className="text-sm">启用</span>
              </div>
            </div>
          </Section>

        {/* 会话管理 - 6 cols */}
        <Section title="会话管理" icon="forum" desc="会话历史与自动保存" className="col-span-6" delay={0.1}>
            <div className="grid grid-cols-2 gap-4">
              <SliderField label="最大历史消息数" value={cfg.session?.max_history_messages ?? 40} min={10} max={200} step={10} onChange={v => updateField('session.max_history_messages', v)} />
              <SliderField label="自动保存间隔 (秒)" value={cfg.session?.auto_save_interval ?? 30} min={5} max={300} step={5} onChange={v => updateField('session.auto_save_interval', v)} />
              <SliderField label="消息最大长度" value={cfg.session?.max_message_length ?? 10000} min={1000} max={50000} step={1000} onChange={v => updateField('session.max_message_length', v)} />
              <div className="flex items-center gap-2">
                <div className="flex items-center">
                  <Toggle checked={cfg.session?.auto_title_generation ?? true} onChange={v => updateField('session.auto_title_generation', v)} />
                </div>
                <span className="text-sm">自动生成标题</span>
              </div>
            </div>
          </Section>

        {/* 网络配置 - 4 cols */}
        <Section title="网络配置" icon="language" desc="代理、超时与连接池" className="col-span-4" delay={0}>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <div className="flex items-center">
                  <Toggle checked={cfg.network?.proxy_enabled ?? false} onChange={v => updateField('network.proxy_enabled', v)} />
                </div>
                <span className="text-sm">启用代理</span>
              </div>
              <Field label="代理地址">
                <input className="input-field" value={cfg.network?.proxy_url || ''} placeholder="http://127.0.0.1:7890" disabled={!(cfg.network?.proxy_enabled)} onChange={e => updateField('network.proxy_url', e.target.value)} style={{ opacity: cfg.network?.proxy_enabled ? 1 : 0.4 }} />
              </Field>
              <SliderField label="请求超时 (秒)" value={cfg.network?.request_timeout ?? 30} min={5} max={120} step={5} onChange={v => updateField('network.request_timeout', v)} />
              <SliderField label="连接超时 (秒)" value={cfg.network?.connect_timeout ?? 10} min={1} max={60} step={1} onChange={v => updateField('network.connect_timeout', v)} />
              <SliderField label="重试次数" value={cfg.network?.retry_count ?? 3} min={0} max={10} step={1} onChange={v => updateField('network.retry_count', v)} />
            </div>
          </Section>

        {/* 日记记录配置 - 8 cols */}
        <Section title="日记记录" icon="book" desc="AI 自动生成日记、周记、月记、年记" className="col-span-8" delay={0.2}>
          <div className="space-y-6">
            {/* 日记 */}
            <div className="bg-black/20 p-4 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-4">
                <div className="font-medium text-[var(--text-primary)]">日记</div>
                <div className="flex items-center">
                  <Toggle
                    checked={cfg.diary?.daily?.enabled ?? false}
                    onChange={(v) => updateField('diary.daily.enabled', v)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-4 mb-3">
                <label className="text-sm text-[var(--text-secondary)]">每</label>
                <input
                  type="number"
                  min="1"
                  value={cfg.diary?.daily?.frequency ?? 1}
                  onChange={(e) => updateField('diary.daily.frequency', parseInt(e.target.value))}
                  className="w-20 px-3 py-1.5 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm"
                />
                <label className="text-sm text-[var(--text-secondary)]">天记录一次</label>
              </div>
              <textarea
                value={cfg.diary?.daily?.prompt ?? ""}
                onChange={(e) => updateField('diary.daily.prompt', e.target.value)}
                placeholder="日记提示词"
                className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm resize-none"
                rows={3}
              />
            </div>

            {/* 周记 */}
            <div className="bg-black/20 p-4 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-4">
                <div className="font-medium text-[var(--text-primary)]">周记</div>
                <div className="flex items-center">
                  <Toggle
                    checked={cfg.diary?.weekly?.enabled ?? false}
                    onChange={(v) => updateField('diary.weekly.enabled', v)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-4 mb-3">
                <label className="text-sm text-[var(--text-secondary)]">每</label>
                <input
                  type="number"
                  min="1"
                  value={cfg.diary?.weekly?.frequency ?? 1}
                  onChange={(e) => updateField('diary.weekly.frequency', parseInt(e.target.value))}
                  className="w-20 px-3 py-1.5 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm"
                />
                <label className="text-sm text-[var(--text-secondary)]">周记录一次</label>
              </div>
              <textarea
                value={cfg.diary?.weekly?.prompt ?? ""}
                onChange={(e) => updateField('diary.weekly.prompt', e.target.value)}
                placeholder="周记提示词"
                className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm resize-none"
                rows={3}
              />
            </div>

            {/* 月记 */}
            <div className="bg-black/20 p-4 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-4">
                <div className="font-medium text-[var(--text-primary)]">月记</div>
                <div className="flex items-center">
                  <Toggle
                    checked={cfg.diary?.monthly?.enabled ?? false}
                    onChange={(v) => updateField('diary.monthly.enabled', v)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-4 mb-3">
                <label className="text-sm text-[var(--text-secondary)]">每</label>
                <input
                  type="number"
                  min="1"
                  value={cfg.diary?.monthly?.frequency ?? 1}
                  onChange={(e) => updateField('diary.monthly.frequency', parseInt(e.target.value))}
                  className="w-20 px-3 py-1.5 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm"
                />
                <label className="text-sm text-[var(--text-secondary)]">月记录一次</label>
              </div>
              <textarea
                value={cfg.diary?.monthly?.prompt ?? ""}
                onChange={(e) => updateField('diary.monthly.prompt', e.target.value)}
                placeholder="月记提示词"
                className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm resize-none"
                rows={3}
              />
            </div>

            {/* 年记 */}
            <div className="bg-black/20 p-4 rounded-lg border border-white/5">
              <div className="flex items-center justify-between mb-4">
                <div className="font-medium text-[var(--text-primary)]">年记</div>
                <div className="flex items-center">
                  <Toggle
                    checked={cfg.diary?.yearly?.enabled ?? false}
                    onChange={(v) => updateField('diary.yearly.enabled', v)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-4 mb-3">
                <label className="text-sm text-[var(--text-secondary)]">每</label>
                <input
                  type="number"
                  min="1"
                  value={cfg.diary?.yearly?.frequency ?? 1}
                  onChange={(e) => updateField('diary.yearly.frequency', parseInt(e.target.value))}
                  className="w-20 px-3 py-1.5 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm"
                />
                <label className="text-sm text-[var(--text-secondary)]">年记录一次</label>
              </div>
              <textarea
                value={cfg.diary?.yearly?.prompt ?? ""}
                onChange={(e) => updateField('diary.yearly.prompt', e.target.value)}
                placeholder="年记提示词"
                className="w-full px-3 py-2 bg-[var(--input-bg)] border border-[var(--border-color)] rounded text-sm resize-none"
                rows={3}
              />
            </div>

            {/* 立即记录按钮 */}
            <button
              onClick={handleImmediateDiary}
              className="w-full py-2 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 text-white rounded transition-colors flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[20px]">edit_note</span>
              <span>立即记录</span>
            </button>
          </div>
        </Section>

        {/* 屏幕截图 - 4 cols */}
        <Section title="屏幕截图" icon="screenshot_monitor" desc="" className="col-span-4" delay={0.1}>
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="text-sm">启用截图</div>
                <div className="text-xs text-gray-500">定时截取屏幕用于视觉感知</div>
              </div>
              <div className="flex items-center">
                <Toggle checked={cfg.action?.screen?.enabled ?? false} onChange={v => updateField('action.screen.enabled', v)} />
              </div>
            </div>
            <SliderField label="截图间隔 (秒)" value={cfg.action?.screen?.interval ?? 30} min={5} max={120} step={5} onChange={v => updateField('action.screen.interval', v)} />
          </div>
        </Section>
      </div>
    </div>
    </ScrollContainerContext.Provider>
  )
}

function Section({ title, icon, desc, className, delay = 0, children }: { title: string; icon: string; desc?: string; className?: string; delay?: number; children: React.ReactNode }) {
  const sectionRef = useRef<HTMLDivElement>(null)
  const scrollRoot = useContext(ScrollContainerContext)

  useEffect(() => {
    const el = sectionRef.current
    if (!el || !scrollRoot) return
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { el.classList.add('visible'); observer.unobserve(el) } },
      { root: scrollRoot, threshold: 0.1 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [scrollRoot])

  return (
    <div
      ref={sectionRef}
      className={`glass-panel rounded-2xl p-6 reveal-section ${className || ''}`}
      style={{ transitionDelay: `${delay}s` }}
    >
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-lg bg-[var(--accent-blue)]/10 flex items-center justify-center text-[var(--accent-blue)]">
          <span className="material-symbols-outlined">{icon}</span>
        </div>
        <div>
          <h3 className="text-base font-medium">{title}</h3>
          {desc && <p className="text-xs text-gray-500">{desc}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">{label}</label>
      {children}
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="inline-flex items-center cursor-pointer interactive-hover">
      <input type="checkbox" className="sr-only peer" checked={checked} onChange={e => onChange(e.target.checked)} />
      <div className="relative w-9 h-5 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent-blue)]" />
    </label>
  )
}

function SliderField({ label, value, min, max, step, onChange, fmt }: {
  label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; fmt?: (v: number) => string
}) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-2">
        <span>{label}</span>
        <span className="font-mono text-[var(--accent-blue)]">{fmt ? fmt(value) : value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(+e.target.value)}
        className="w-full h-1 bg-gray-700 rounded-full appearance-none [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--accent-blue)] [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-[#1a1a1a]" />
    </div>
  )
}
