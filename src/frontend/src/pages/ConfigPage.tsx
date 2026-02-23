import { useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import { api } from '../api/client'

const ACCENT_COLORS = ['#60cdff', '#ff6060', '#60ff8b', '#ffc460', '#c260ff']
const ENGINES = ['vllm', 'transformers', 'llama.cpp'] as const
const EMBEDDING_MODELS = ['text-embedding-3-small', 'm3e-base', 'bge-large-zh'] as const
const ASR_SIZES = ['tiny', 'base', 'small', 'medium', 'large-v3'] as const
const COMPUTE_TYPES = ['float16', 'int8_float16', 'int8'] as const

const EMOTION_COLORS: Record<string, string> = {
  happy: 'bg-yellow-400', angry: 'bg-red-400', sad: 'bg-blue-400', neutral: 'bg-gray-400',
  shy: 'bg-pink-400', excited: 'bg-orange-400', surprised: 'bg-purple-400',
}

export default function ConfigPage() {
  const [cfg, setCfg] = useState<any>(null)
  const [saved, setSaved] = useState(false)
  const [refs, setRefs] = useState<{ emotion: string; file: string }[]>([])
  const [inputDevices, setInputDevices] = useState<{ index: number; name: string }[]>([])
  const [outputDevices, setOutputDevices] = useState<{ index: number; name: string }[]>([])
  const [micLevel, setMicLevel] = useState(-1)
  const [micTesting, setMicTesting] = useState(false)
  const micSocketRef = useRef<ReturnType<typeof io> | null>(null)

  useEffect(() => {
    api.get('/config').then(r => setCfg(r.data))
    api.get('/emotion-refs').then(r => setRefs(r.data)).catch(() => {})
    api.get('/asr/devices').then(r => setInputDevices(r.data)).catch(() => {})
    api.get('/asr/output-devices').then(r => setOutputDevices(r.data)).catch(() => {})
  }, [])

  const set = (path: string, value: any) => {
    const copy = JSON.parse(JSON.stringify(cfg))
    const keys = path.split('.')
    let obj = copy
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {}
      obj = obj[keys[i]]
    }
    obj[keys[keys.length - 1]] = value
    setCfg(copy)
    if (path === 'general.accent_color') document.documentElement.style.setProperty('--accent-blue', value)
    if (path === 'general.dark_mode') document.documentElement.classList.toggle('light', !value)
  }

  useEffect(() => {
    if (!cfg) return
    if (cfg.general?.accent_color) document.documentElement.style.setProperty('--accent-blue', cfg.general.accent_color)
    document.documentElement.classList.toggle('light', !(cfg.general?.dark_mode ?? true))
  }, [cfg?.general?.accent_color, cfg?.general?.dark_mode])

  useEffect(() => {
    return () => { micSocketRef.current?.disconnect() }
  }, [])

  const save = () => {
    api.put('/config', cfg).then(() => { setSaved(true); setTimeout(() => setSaved(false), 2000) })
  }

  const reset = () => { api.get('/config').then(r => setCfg(r.data)) }

  const startMicTest = () => {
    const device = cfg?.perception?.asr?.mic_device ?? null
    setMicTesting(true)
    setMicLevel(0)
    micSocketRef.current?.disconnect()
    const s = io('/ws/events')
    micSocketRef.current = s
    s.on('mic_level', (d: { level: number }) => {
      if (d.level < 0) { setMicTesting(false); setMicLevel(-1); s.disconnect(); micSocketRef.current = null; return }
      setMicLevel(d.level)
    })
    api.post('/asr/mic-test', { device }).catch(() => { setMicTesting(false); s.disconnect(); micSocketRef.current = null })
  }

  const stopMicTest = () => {
    setMicTesting(false)
    setMicLevel(-1)
    micSocketRef.current?.disconnect()
    micSocketRef.current = null
    api.post('/asr/mic-test-stop').catch(() => {})
  }

  if (!cfg) return <div className="p-6 text-gray-400">Loading...</div>

  return (
    <div className="p-6 h-full overflow-y-auto custom-scrollbar flex flex-col gap-6">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white">系统配置</h1>
          <p className="text-xs text-gray-500 mt-1">配置外观、核心 AI 大脑、感知模型和记忆向量。</p>
        </div>
        <div className="flex gap-3">
          <button onClick={reset} className="glass-panel px-4 py-2 text-sm font-medium flex items-center gap-2 text-white rounded-lg hover:bg-white/10 transition-colors">
            <span className="material-symbols-outlined text-[18px]">restart_alt</span>重置
          </button>
          <button onClick={save} className="px-5 py-2 bg-[var(--accent-blue)] text-black text-sm font-medium rounded-lg hover:bg-cyan-300 transition-colors flex items-center gap-2 shadow-[0_0_15px_rgba(96,205,255,0.3)]">
            <span className="material-symbols-outlined text-[18px]">save</span>
            {saved ? '✓ 已保存' : '保存配置'}
          </button>
        </div>
      </div>

      {/* General Settings */}
      <Section title="通用设置" icon="tune" desc="应用外观与主题偏好">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-4 bg-black/20 rounded-lg border border-white/5">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-gray-400">dark_mode</span>
              <div><div className="text-sm font-medium">深色模式</div><div className="text-xs text-gray-500">启用全局深色主题</div></div>
            </div>
            <Toggle checked={cfg.general?.dark_mode ?? true} onChange={v => set('general.dark_mode', v)} />
          </div>
          <div className="flex items-center justify-between p-4 bg-black/20 rounded-lg border border-white/5">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-gray-400">palette</span>
              <div><div className="text-sm font-medium">主题色</div><div className="text-xs text-gray-500">选择系统高亮颜色</div></div>
            </div>
            <div className="flex gap-2">
              {ACCENT_COLORS.map(c => (
                <div key={c} onClick={() => set('general.accent_color', c)}
                  className={`w-6 h-6 rounded-full cursor-pointer border-2 transition-all hover:scale-110 ${cfg.general?.accent_color === c ? 'border-white shadow-[0_0_0_2px_rgba(255,255,255,0.2)]' : 'border-transparent'}`}
                  style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
        </div>
      </Section>

      <div className="grid grid-cols-12 gap-6">
        {/* Left column: Brain + Memory */}
        <div className="col-span-8 space-y-6">
          {/* Core Cognition */}
          <Section title="核心认知 (Brain Layer)" icon="psychology" desc="管理 LLM 推理引擎和模型权重">
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-2">推理后端</label>
                  <div className="flex p-1 bg-black/30 rounded-lg border border-white/5">
                    {ENGINES.map(e => (
                      <button key={e} onClick={() => set('brain.engine', e)}
                        className={`flex-1 py-2 text-xs font-medium rounded transition-colors ${cfg.brain?.engine === e ? 'bg-white/10 shadow text-white border border-white/10' : 'text-gray-500 hover:text-white'}`}>
                        {e === 'vllm' ? 'vLLM (CUDA)' : e === 'transformers' ? 'Transformers' : 'Llama.cpp'}
                      </button>
                    ))}
                  </div>
                </div>
                <Field label="本地模型路径">
                  <input className="input-field" value={cfg.brain?.model_path || ''} onChange={e => set('brain.model_path', e.target.value)} />
                </Field>
                <div className="flex items-center justify-between py-2 border-b border-white/5">
                  <div><div className="text-sm">GPU 显存占用</div><div className="text-xs text-gray-500">限制 VRAM 使用 (0.1 - 0.95)</div></div>
                  <input type="number" step={0.05} className="input-field w-20 text-center text-sm" value={cfg.brain?.gpu_memory_utilization ?? 0.85} onChange={e => set('brain.gpu_memory_utilization', +e.target.value)} />
                </div>
                <Field label="启用思考">
                  <Toggle checked={cfg.brain?.enable_thinking ?? false} onChange={v => set('brain.enable_thinking', v)} />
                </Field>
              </div>
              <div className="bg-black/20 p-5 rounded-lg border border-white/5 space-y-4">
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">生成参数</h4>
                <SliderField label="Temperature" value={cfg.brain?.temperature ?? 0.7} min={0} max={2} step={0.1} onChange={v => set('brain.temperature', v)} />
                <SliderField label="Top_P" value={cfg.brain?.top_p ?? 0.9} min={0} max={1} step={0.05} onChange={v => set('brain.top_p', v)} />
                <SliderField label="最大 Tokens" value={cfg.brain?.max_tokens ?? 4096} min={512} max={8192} step={512} onChange={v => set('brain.max_tokens', v)} />
                <SliderField label="上下文长度" value={cfg.brain?.context_length ?? 8192} min={2048} max={32768} step={1024} onChange={v => set('brain.context_length', v)} fmt={v => v >= 1024 ? `${Math.round(v/1024)}k` : String(v)} />
              </div>
            </div>
          </Section>

          {/* Long-term Memory */}
          <Section title="长期记忆 (ChromaDB)" icon="database" desc="">
            <div className="grid grid-cols-2 gap-4">
              <Field label="集合名称">
                <input className="input-field" value={cfg.memory?.collection_name || ''} onChange={e => set('memory.collection_name', e.target.value)} />
              </Field>
              <Field label="嵌入模型">
                <select className="input-field" value={cfg.memory?.embedding_model || 'm3e-base'} onChange={e => set('memory.embedding_model', e.target.value)}>
                  {EMBEDDING_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </Field>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Toggle checked={cfg.memory?.auto_persist ?? true} onChange={v => set('memory.auto_persist', v)} />
                <span className="text-sm">自动持久化</span>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <Toggle checked={cfg.memory?.enabled ?? false} onChange={v => set('memory.enabled', v)} />
                <span className="text-sm">启用</span>
              </div>
            </div>
          </Section>
        </div>

        {/* Right column: TTS + ASR */}
        <div className="col-span-4 space-y-6">
          {/* TTS */}
          <Section title="语音合成 (GPT-SoVITS)" icon="record_voice_over" desc="">
            <div className="space-y-4">
              <Field label="API 地址">
                <input className="input-field" value={cfg.perception?.tts?.api_url || ''} onChange={e => set('perception.tts.api_url', e.target.value)} />
              </Field>
              <Field label="SoVITS Weights (.pth)">
                <input className="input-field font-mono text-xs" value={cfg.perception?.tts?.sovits_weights || cfg.perception?.tts?.model_path || ''} onChange={e => set('perception.tts.sovits_weights', e.target.value)} />
              </Field>
              <Field label="GPT Weights (.ckpt)">
                <input className="input-field font-mono text-xs" value={cfg.perception?.tts?.gpt_weights || ''} onChange={e => set('perception.tts.gpt_weights', e.target.value)} />
              </Field>
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

          {/* ASR */}
          <Section title="语音识别 (ASR)" icon="mic" desc="">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">模型大小</span>
                <select className="input-field w-32 py-1 text-xs" value={cfg.perception?.asr?.model_size || 'medium'} onChange={e => set('perception.asr.model_size', e.target.value)}>
                  {ASR_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">计算精度</span>
                <select className="input-field w-32 py-1 text-xs" value={cfg.perception?.asr?.compute_type || 'int8'} onChange={e => set('perception.asr.compute_type', e.target.value)}>
                  {COMPUTE_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <SliderField label="VAD 灵敏度" value={cfg.perception?.asr?.vad_threshold ?? 0.2} min={0} max={1} step={0.1} onChange={v => set('perception.asr.vad_threshold', v)} />
              <div className="flex items-center justify-between">
                <span className="text-sm">输入设备</span>
                <select className="input-field w-48 py-1 text-xs" value={cfg.perception?.asr?.mic_device ?? ''} onChange={e => set('perception.asr.mic_device', e.target.value === '' ? null : +e.target.value)}>
                  <option value="">默认</option>
                  {inputDevices.map(d => <option key={d.index} value={d.index}>{d.name}</option>)}
                </select>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">输出设备</span>
                <select className="input-field w-48 py-1 text-xs" value={cfg.perception?.tts?.output_device ?? ''} onChange={e => set('perception.tts.output_device', e.target.value === '' ? null : +e.target.value)}>
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

          {/* Screenshot */}
          <Section title="屏幕截图" icon="screenshot_monitor" desc="">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div><div className="text-sm">启用截图</div><div className="text-xs text-gray-500">定时截取屏幕用于视觉感知</div></div>
                <Toggle checked={cfg.action?.screen?.enabled ?? false} onChange={v => set('action.screen.enabled', v)} />
              </div>
              <SliderField label="截图间隔 (秒)" value={cfg.action?.screen?.interval ?? 30} min={5} max={120} step={5} onChange={v => set('action.screen.interval', v)} />
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}

function Section({ title, icon, desc, children }: { title: string; icon: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="glass-panel rounded-xl p-6">
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
    <label className="inline-flex items-center cursor-pointer">
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
