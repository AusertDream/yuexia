export default function LivePreview() {
  return (
    <div className="glass-panel rounded-xl overflow-hidden relative flex flex-col h-full">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--accent-blue)] to-transparent opacity-50" />
      <div className="p-3 border-b border-gray-700/50 flex justify-between items-center bg-black/20">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-sm text-[var(--accent-blue)]">visibility</span>
          <span className="text-xs font-mono font-bold tracking-wider uppercase text-gray-300">实时预览</span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] bg-green-500/10 text-green-400 border border-green-500/20 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> LIVE
        </span>
      </div>
      <div className="flex-1 bg-gradient-to-b from-[#1a1d24] to-[#0f1115] relative">
        <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <iframe src="/live2d/index.html" className="absolute inset-0 w-full h-full border-0" title="Live2D" />
      </div>
    </div>
  )
}
