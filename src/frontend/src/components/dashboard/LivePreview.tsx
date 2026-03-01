import { useState, useEffect } from 'react'

export default function LivePreview({ fullscreen = false }: { fullscreen?: boolean }) {
  const [locked, setLocked] = useState(() => {
    try { return localStorage.getItem('live2d-locked') === 'true' } catch { return false }
  })
  useEffect(() => {
    try { localStorage.setItem('live2d-locked', String(locked)) } catch {}
  }, [locked])
  if (fullscreen) {
    return (
      <div className="absolute inset-0 w-full h-full">
        <iframe src="/live2d/index.html" className="absolute inset-0 w-full h-full border-0" title="Live2D" />
        {locked && (
          <div className="absolute inset-0" style={{ pointerEvents: 'auto' }} />
        )}
        <button
          onClick={() => setLocked(v => !v)}
          className="absolute top-4 left-4 z-20 p-2 rounded-lg backdrop-blur-sm border transition-colors"
          style={{
            background: locked ? 'rgba(239,68,68,0.15)' : 'rgba(0,0,0,0.3)',
            borderColor: locked ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.1)',
            color: locked ? '#f87171' : 'rgba(255,255,255,0.6)',
          }}
          title={locked ? '点击解锁 Live2D' : '点击锁定 Live2D'}
        >
          <span className="material-symbols-outlined text-[20px]">
            {locked ? 'lock' : 'lock_open'}
          </span>
        </button>
      </div>
    )
  }

  return (
    <div className="glass-panel rounded-xl overflow-hidden relative flex flex-col h-full">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--accent-blue)] to-transparent opacity-50" />
      <div className="p-3 border-b border-gray-700/50 flex justify-between items-center bg-[var(--panel-bg)]/20">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-sm text-[var(--accent-blue)]">visibility</span>
          <span className="text-xs font-mono font-bold tracking-wider uppercase text-gray-300">实时预览</span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] bg-green-500/10 text-green-400 border border-green-500/20 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> LIVE
        </span>
      </div>
      <div className="flex-1 bg-gradient-to-b from-[var(--panel-bg-alt)] to-[var(--panel-bg)] relative">
        <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <iframe src="/live2d/index.html" className="absolute inset-0 w-full h-full border-0" title="Live2D" />
      </div>
    </div>
  )
}
