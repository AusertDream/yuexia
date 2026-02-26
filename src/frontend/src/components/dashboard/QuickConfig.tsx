import { useEffect } from 'react'
import { useConfigStore } from '../../stores'

export default function QuickConfig() {
  const { config: cfg, loadConfig, updateField, saveConfig } = useConfigStore()

  useEffect(() => {
    // 如果 store 中没有配置，加载一次
    if (!cfg) loadConfig()
  }, [cfg, loadConfig])

  const update = (path: string, value: any) => {
    updateField(path, value)
    // 延迟保存，确保 store 状态已更新
    setTimeout(() => saveConfig(), 0)
  }

  return (
    <div className="glass-panel rounded-xl p-5 relative overflow-hidden h-full">
      <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider mb-4 flex items-center gap-2">
        <span className="material-symbols-outlined text-purple-400">tune</span>
        快捷配置
      </h2>
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-2">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">推理引擎</label>
          <select
            className="w-full bg-[var(--input-bg)] border border-[var(--border-color)] text-[var(--input-text)] text-sm rounded-lg p-2.5"
            value={cfg?.brain?.engine || 'transformers'}
            onChange={e => update('brain.engine', e.target.value)}
          >
            <option value="transformers">Transformers</option>
            <option value="vllm">vLLM</option>
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">模型路径</label>
          <input
            className="w-full bg-[var(--input-bg)] border border-[var(--border-color)] text-[var(--input-text)] text-sm rounded-lg p-2.5"
            value={cfg?.brain?.model_path || ''}
            onChange={e => update('brain.model_path', e.target.value)}
          />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-4">
        <label className="inline-flex items-center cursor-pointer">
          <input type="checkbox" className="sr-only peer" checked={cfg?.brain?.stream ?? true} onChange={e => update('brain.stream', e.target.checked)} />
          <div className="relative w-9 h-5 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent-blue)]" />
          <span className="ms-3 text-xs font-medium text-gray-400">流式输出</span>
        </label>
        <label className="inline-flex items-center cursor-pointer">
          <input type="checkbox" className="sr-only peer" checked={cfg?.memory?.enabled ?? false} onChange={e => update('memory.enabled', e.target.checked)} />
          <div className="relative w-9 h-5 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent-blue)]" />
          <span className="ms-3 text-xs font-medium text-gray-400">记忆检索</span>
        </label>
      </div>
    </div>
  )
}
