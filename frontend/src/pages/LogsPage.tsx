import { useRef, useState } from 'react'
import { useLogSocket } from '../hooks/useWebSocket'

const LEVELS = ['ALL', 'INFO', 'WARNING', 'ERROR'] as const
const LEVEL_COLORS: Record<string, string> = {
  INFO: 'text-blue-400', WARNING: 'text-yellow-400', ERROR: 'text-red-400', DEBUG: 'text-gray-500',
}

export default function LogsPage() {
  const logs = useLogSocket()
  const [filter, setFilter] = useState<string>('ALL')
  const [search, setSearch] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  const filtered = logs.filter(l => {
    if (filter !== 'ALL' && l.level !== filter) return false
    if (search && !l.message.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  if (autoScroll && scrollRef.current) {
    setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 0)
  }

  const download = () => {
    const text = filtered.map(l => `[${l.time}] [${l.level}] [${l.module}] ${l.message}`).join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `logs_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="material-symbols-outlined text-[var(--accent-blue)]">data_object</span>
            系统执行日志
          </h1>
          <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            实时流已连接
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-[18px]">search</span>
            <input
              className="bg-[#111722] border border-white/10 text-white text-sm rounded-lg pl-9 pr-3 py-2 w-56 placeholder-gray-600 focus:ring-1 focus:ring-[var(--accent-blue)] focus:border-[var(--accent-blue)]"
              placeholder="过滤日志..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="h-6 w-px bg-white/10" />
          {/* Level filters */}
          <div className="flex bg-[#111722] rounded-lg p-1 border border-white/10">
            {LEVELS.map(l => (
              <button key={l} onClick={() => setFilter(l)}
                className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${filter === l ? 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border border-[var(--accent-blue)]/30' : 'text-gray-400 hover:text-white'}`}>
                {l === 'WARNING' ? '警告' : l === 'ALL' ? '全部' : l === 'INFO' ? '信息' : '错误'}
              </button>
            ))}
          </div>
          <div className="h-6 w-px bg-white/10" />
          {/* Download */}
          <button onClick={download} title="下载日志"
            className="p-2.5 rounded-lg text-gray-400 hover:bg-white/5 hover:text-white transition-colors border border-transparent hover:border-white/10">
            <span className="material-symbols-outlined text-[20px]">download</span>
          </button>
          {/* Clear */}
          <button onClick={() => { /* logs come from socket, no local clear */ }}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#232f48] hover:bg-[#2c3b59] text-white text-sm font-medium rounded-lg transition-colors border border-white/5">
            <span className="material-symbols-outlined text-[18px]">delete_sweep</span>清除
          </button>
        </div>
      </div>

      {/* Terminal */}
      <div className="flex-1 bg-[#0d1117] rounded-xl border border-white/10 shadow-2xl overflow-hidden flex flex-col font-mono text-sm">
        {/* Terminal header */}
        <div className="h-8 bg-[#161b22] border-b border-white/5 flex items-center px-4 justify-between select-none">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/80" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
            <div className="w-3 h-3 rounded-full bg-green-500/80" />
          </div>
          <div className="text-[10px] text-gray-600 font-medium tracking-wide">终端 — 日志监控 — 120x40</div>
          <span className="material-symbols-outlined text-gray-600 text-[16px]">more_horiz</span>
        </div>

        {/* Log content */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-1 custom-scrollbar">
          {filtered.map((l, i) => (
            <div key={i} className={`flex gap-3 p-0.5 rounded px-2 hover:bg-white/5 ${l.level === 'ERROR' ? 'bg-red-500/5 text-red-100' : l.level === 'WARNING' ? 'text-yellow-100' : 'text-gray-300'}`}>
              <span className="text-gray-500 flex-shrink-0 w-24 select-none">[{l.time}]</span>
              <span className={`font-bold flex-shrink-0 w-16 select-none ${LEVEL_COLORS[l.level] || 'text-gray-400'}`}>{l.level}</span>
              <span className="text-gray-400 flex-shrink-0 w-24 select-none">{l.module}</span>
              <span>{l.message}</span>
            </div>
          ))}
          {filtered.length === 0 && <div className="text-gray-500 px-2">等待日志...</div>}
        </div>

        {/* Status bar */}
        <div className="h-6 bg-[#161b22] border-t border-white/5 flex items-center justify-between px-3 text-[10px] text-gray-600">
          <div className="flex gap-4">
            <span>Ln {filtered.length}, Col 1</span>
            <span>UTF-8</span>
          </div>
          <button onClick={() => setAutoScroll(v => !v)} className="flex items-center gap-1 cursor-pointer hover:text-white transition-colors">
            <span className="material-symbols-outlined text-[12px]">vertical_align_bottom</span>
            自动滚动: {autoScroll ? '开' : '关'}
          </button>
        </div>
      </div>
    </div>
  )
}
