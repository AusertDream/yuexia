import { useSystemStore } from '../../stores'

export default function SystemStatusPanel() {
  const status = useSystemStore(s => s.status)

  const gpu = status?.gpu
  const vramPct = gpu ? Math.round((gpu.mem_used / gpu.mem_total) * 100) : 0
  const gpuLoadPct = gpu?.load ?? 0
  const hasError = status ? Object.values(status.loading_status ?? {}).some(v => typeof v === 'string' && v.startsWith('error')) : false

  return (
    <div className="glass-panel rounded-xl p-5 flex flex-col gap-4 h-full">
      <div className="flex justify-between items-center mb-1">
        <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
          <span className="material-symbols-outlined text-[var(--accent-blue)]">monitoring</span>
          系统状态
        </h2>
        <span className={`text-xs font-mono ${hasError ? 'text-red-400' : status?.services_ready ? 'text-emerald-500' : 'text-yellow-500 animate-pulse'}`}>
          {hasError ? '部分服务异常' : status?.services_ready ? '所有服务就绪' : '服务加载中...'}
        </span>
      </div>

      {/* Service loading status */}
      {status && (!status.services_ready || hasError) && (
        <div className="flex flex-wrap gap-2 -mt-2">
          {Object.entries(status.loading_status ?? {}).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--panel-bg)]/20 border border-[var(--border-color)] text-[11px] font-mono">
              <span className={`w-1.5 h-1.5 rounded-full ${v === 'ok' ? 'bg-emerald-500' : v === 'loading' ? 'bg-yellow-500 animate-pulse' : v === 'pending' ? 'bg-gray-600' : 'bg-red-500'}`} />
              <span className="text-gray-400">{k}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 flex-1">
        {/* GPU */}
        <div className="bg-[var(--panel-bg)]/20 rounded-lg p-3 border border-[var(--border-color)] flex flex-col justify-between">
          <div>
            <div className="text-[10px] text-gray-500 uppercase font-mono">显卡 {gpu?.name ? `• ${gpu.name}` : ''}</div>
            <div className="text-2xl font-mono font-bold text-white mt-1">
              {gpu ? gpu.mem_used.toFixed(1) : '--'} <span className="text-sm text-gray-500 font-normal">GB</span>
            </div>
          </div>
          <div className="space-y-2 mt-3">
            <div className="flex justify-between text-[10px] text-gray-400">
              <span>显存占用 ({vramPct}%)</span>
              <span className="text-[var(--accent-blue)]">{gpu ? `${gpu.mem_used.toFixed(1)} / ${gpu.mem_total.toFixed(0)} GB` : '--'}</span>
            </div>
            <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-500 to-[var(--accent-blue)] status-bar-fill rounded-full transition-all" style={{ width: `${vramPct}%` }} />
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 mt-2">
              <span>GPU 利用率 ({gpuLoadPct}%)</span>
            </div>
            <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all" style={{ width: `${gpuLoadPct}%` }} />
            </div>
          </div>
        </div>
        {/* CPU */}
        <div className="bg-[var(--panel-bg)]/20 rounded-lg p-3 border border-[var(--border-color)] flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-[10px] text-gray-500 uppercase font-mono">CPU 负载</div>
              <div className="text-2xl font-mono font-bold text-white mt-1">
                {status ? Math.round(status.cpu_percent) : '--'} <span className="text-sm text-gray-500 font-normal">%</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-gray-500 uppercase font-mono">系统内存</div>
              <div className="text-sm font-mono text-gray-300">
                {status ? `${status.ram_used} / ${status.ram_total} GB` : '--'}
              </div>
            </div>
          </div>
          <div className="flex justify-between items-center mt-3 pt-2 border-t border-[var(--border-color)]/30">
            <span className="text-[10px] text-gray-500 uppercase font-mono">推理速度</span>
            <span className="text-sm font-mono text-[var(--accent-blue)]">{status?.inference_speed ? `${status.inference_speed} chunks/s` : '--'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
