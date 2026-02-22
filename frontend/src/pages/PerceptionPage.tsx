import { useEffect, useState } from 'react'
import { io } from 'socket.io-client'
import { api } from '../api/client'

interface AsrEntry { time: string; role: string; text: string }
interface MotorEntry { time: string; signal: string; confidence: number; target: string; status: string }

const STATUS_STYLES: Record<string, string> = {
  Executing: 'bg-blue-500 text-white animate-pulse',
  Queued: 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/20',
  Completed: 'bg-[#1b212d] text-gray-500 border border-gray-700',
  Looping: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
  Error: 'bg-red-500/20 text-red-400 border border-red-500/20',
}

const MOTOR_FILTERS = ['全部信号', '活跃', '错误'] as const

export default function PerceptionPage() {
  const [asrLog, setAsrLog] = useState<AsrEntry[]>([])
  const [motorFilter, setMotorFilter] = useState<string>('全部信号')
  const [serviceStatus, setServiceStatus] = useState<Record<string, string>>({})
  const [motors] = useState<MotorEntry[]>([
    { time: '--:--:--.--', signal: 'Idle_Breathing', confidence: 100, target: 'Global_Body', status: 'Looping' },
  ])

  useEffect(() => {
    const s = io('/ws/events')
    s.on('asr_result', (d: { text: string }) => {
      setAsrLog(prev => [...prev.slice(-99), { time: new Date().toLocaleTimeString(), role: 'USER', text: d.text }])
    })
    return () => { s.disconnect() }
  }, [])

  useEffect(() => {
    const poll = () => api.get('/system/status').then(r => setServiceStatus(r.data.loading_status ?? {})).catch(() => {})
    poll()
    const id = setInterval(poll, 5000)
    return () => clearInterval(id)
  }, [])

  const filteredMotors = motors.filter(m => {
    if (motorFilter === '活跃') return m.status === 'Executing' || m.status === 'Looping'
    if (motorFilter === '错误') return m.status === 'Error'
    return true
  })

  return (
    <div className="p-6 h-full flex flex-col gap-6 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span className="material-symbols-outlined text-[var(--accent-blue)]">visibility</span>
            感知与动作层
          </h1>
          <p className="text-xs text-gray-500 font-mono">实时感知输入与动作输出追踪</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge icon="videocam" label="摄像头" online={false} />
          <StatusBadge icon="mic" label="麦克风" online={serviceStatus.perception === 'ok'} />
          <StatusBadge icon="screenshot_monitor" label="截图" online />
        </div>
      </header>

      {/* Upper: Perception */}
      <section className="flex-1 flex gap-6 min-h-[250px]">
        {/* Visual Input */}
        <div className="w-1/3 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">视觉输入</h3>
            <span className="text-[10px] font-mono text-gray-500 bg-[#1b212d] px-1.5 rounded">1080p | 30fps</span>
          </div>
          <VisualFeed />
        </div>

        {/* ASR Stream */}
        <div className="w-2/3 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">语音识别文本流</h3>
            <button onClick={() => setAsrLog([])} className="text-[10px] uppercase font-bold text-[var(--accent-blue)] hover:text-[var(--accent-blue)]/80">清除</button>
          </div>
          <div className="flex-1 rounded-xl border border-gray-700/50 bg-[#0a0c10] p-4 overflow-y-auto font-mono text-sm relative">
            <div className="absolute top-2 right-2"><div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" /></div>
            <div className="flex flex-col gap-3">
              {asrLog.map((e, i) => (
                <div key={i} className="flex gap-3">
                  <span className="text-gray-500 min-w-[80px] text-[11px] pt-1">[{e.time}]</span>
                  <div className="flex flex-col">
                    <span className={`text-xs font-bold mb-0.5 ${e.role === 'USER' ? 'text-sky-400' : 'text-emerald-400'}`}>{e.role}</span>
                    <span className="text-gray-300">{e.text}</span>
                  </div>
                </div>
              ))}
              {asrLog.length === 0 && (
                <div className="flex gap-3 border-l-2 border-[var(--accent-blue)] pl-3 bg-[var(--accent-blue)]/5 py-2 rounded-r">
                  <span className="text-gray-500 min-w-[80px] text-[11px] pt-1">LIVE</span>
                  <div><span className="text-gray-400 text-xs">监听中...</span><br /><span className="text-white animate-pulse">...</span></div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="h-px w-full bg-gray-700/50 relative flex items-center justify-center">
        <div className="bg-[#0b0f17] px-4 text-xs font-mono text-gray-500">层间接口</div>
      </div>

      {/* Lower: Motor Output */}
      <section className="flex-1 flex flex-col gap-2 min-h-0">
        <div className="flex justify-between items-end">
          <div>
            <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">动作输出 (月下协议)</h3>
            <p className="text-xs text-gray-500 mt-1">实时信号队列与执行状态</p>
          </div>
          <div className="flex gap-2">
            {MOTOR_FILTERS.map(f => (
              <button key={f} onClick={() => setMotorFilter(f)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${motorFilter === f ? 'bg-[var(--accent-blue)] text-white shadow-lg shadow-[var(--accent-blue)]/20' : 'bg-[#1b212d] text-gray-400 border border-gray-700 hover:border-gray-500'}`}>
                {f}
              </button>
            ))}
          </div>
        </div>
        <MotorTable motors={filteredMotors} />
      </section>
    </div>
  )
}

function StatusBadge({ icon, label, online }: { icon: string; label: string; online: boolean }) {
  const color = online ? 'text-emerald-500' : 'text-red-400'
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#1b212d] border border-gray-700">
      <span className={`material-symbols-outlined ${color} text-[16px]`}>{icon}</span>
      <span className={`text-xs font-mono ${color}`}>{label}: {online ? '开' : '关'}</span>
    </div>
  )
}

function VisualFeed() {
  const [img, setImg] = useState<string | null>(null)

  useEffect(() => {
    const poll = () => api.get('/screenshot').then(r => setImg(r.data.image)).catch(() => {})
    poll()
    const id = setInterval(poll, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="relative flex-1 rounded-xl overflow-hidden border border-gray-700/50 bg-black">
      {img ? (
        <img src={img} alt="截图" className="absolute inset-0 w-full h-full object-cover" />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
          <span className="material-symbols-outlined text-gray-700 text-6xl">videocam_off</span>
        </div>
      )}
      <div className="absolute top-2 left-2 border border-[var(--accent-blue)]/50 text-[var(--accent-blue)] text-[10px] font-mono px-1 bg-[var(--accent-blue)]/10 backdrop-blur-sm">
        {img ? '截图 ●' : '等待截图...'}
      </div>
    </div>
  )
}

function MotorTable({ motors }: { motors: MotorEntry[] }) {
  return (
    <div className="flex-1 bg-[#1b212d] rounded-xl border border-gray-700/50 overflow-hidden flex flex-col">
      <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b border-gray-700/50 bg-[#161b24] text-xs font-medium text-gray-400 uppercase tracking-wider">
        <div className="col-span-2">时间</div>
        <div className="col-span-3">信号 / 协议</div>
        <div className="col-span-3">置信度</div>
        <div className="col-span-2">目标</div>
        <div className="col-span-2 text-right">状态</div>
      </div>
      <div className="overflow-y-auto flex-1 p-2 space-y-1">
        {motors.map((m, i) => (
          <div key={i} className={`grid grid-cols-12 gap-4 px-3 py-3 rounded hover:bg-white/5 items-center transition-colors ${m.status === 'Executing' ? 'border-l-2 border-[var(--accent-blue)] bg-[var(--accent-blue)]/5' : 'border-l-2 border-transparent'} ${m.status === 'Completed' ? 'opacity-60' : ''}`}>
            <div className="col-span-2 text-xs font-mono text-gray-400">{m.time}</div>
            <div className="col-span-3 text-sm font-medium text-gray-200">{m.signal}</div>
            <div className="col-span-3 pr-4">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-[#101622] rounded-full overflow-hidden">
                  <div className="h-full bg-[var(--accent-blue)] rounded-full" style={{ width: `${m.confidence}%` }} />
                </div>
                <span className="text-xs font-mono text-gray-400">{m.confidence === 100 && m.status === 'Looping' ? 'N/A' : `${m.confidence}%`}</span>
              </div>
            </div>
            <div className="col-span-2 text-xs text-gray-400">{m.target}</div>
            <div className="col-span-2 flex justify-end">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${STATUS_STYLES[m.status] || STATUS_STYLES.Completed}`}>{m.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
