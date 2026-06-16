import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import MarkdownRenderer from '../components/chat/MarkdownRenderer'

interface DiaryEntry {
  name: string
  type: string
  date: string
  time: string
  title: string
  preview: string
}

interface DiaryDetail {
  name: string
  type: string
  date: string
  time: string
  content: string
}

const TYPE_LABEL: Record<string, string> = {
  daily: '日记', weekly: '周记', monthly: '月记', yearly: '年记',
}

const TYPE_BADGE: Record<string, string> = {
  daily: 'bg-sky-500/15 text-sky-400 border-sky-500/25',
  weekly: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
  monthly: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  yearly: 'bg-violet-500/15 text-violet-400 border-violet-500/25',
}

const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'daily', label: '日记' },
  { key: 'weekly', label: '周记' },
  { key: 'monthly', label: '月记' },
  { key: 'yearly', label: '年记' },
] as const

export default function DiaryPage() {
  const [entries, setEntries] = useState<DiaryEntry[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [selected, setSelected] = useState<DiaryDetail | null>(null)
  const [listLoading, setListLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setListLoading(true)
    api.get('/diary')
      .then(r => { if (alive) setEntries(r.data?.entries ?? []) })
      .catch(() => { if (alive) setError('日记列表加载失败') })
      .finally(() => { if (alive) setListLoading(false) })
    return () => { alive = false }
  }, [])

  const openEntry = useCallback((name: string) => {
    setDetailLoading(true)
    setError('')
    api.get(`/diary/${encodeURIComponent(name)}`)
      .then(r => setSelected(r.data))
      .catch(() => setError('日记内容加载失败'))
      .finally(() => setDetailLoading(false))
  }, [])

  const filtered = filter === 'all' ? entries : entries.filter(e => e.type === filter)

  return (
    <div className="p-6 h-full flex flex-col gap-6 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-2">
            <span className="material-symbols-outlined text-[var(--accent-blue)]" aria-hidden="true">auto_stories</span>
            内心世界
          </h1>
          <p className="text-xs text-gray-500 font-mono">她写下的日记 · 周记 · 月记 · 年记</p>
        </div>
        <span className="text-xs font-mono text-gray-500 bg-[var(--badge-bg)] px-2 py-1 rounded tabular-nums">
          {entries.length} 篇
        </span>
      </header>

      {/* Body: 左右双栏 */}
      <div className="flex-1 flex gap-6 min-h-0">
        {/* 左栏：筛选 + 列表 */}
        <div className="w-1/3 max-w-sm flex flex-col gap-3 min-h-0">
          <div className="flex gap-1.5 flex-wrap flex-shrink-0" role="tablist" aria-label="日记类型筛选">
            {FILTERS.map(f => (
              <button
                key={f.key}
                role="tab"
                aria-selected={filter === f.key}
                onClick={() => setFilter(f.key)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-blue)] ${
                  filter === f.key
                    ? 'bg-[var(--accent-blue)] text-white shadow-lg shadow-[var(--accent-blue)]/20'
                    : 'bg-[var(--badge-bg)] text-gray-400 border border-gray-700 hover:border-gray-500 hover:text-gray-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar rounded-xl border border-gray-700/50 bg-[var(--header-bg)] p-2 [overscroll-behavior:contain]">
            {listLoading ? (
              <p className="text-sm text-gray-500 p-4 animate-pulse">加载中…</p>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center gap-2 py-12">
                <span className="material-symbols-outlined text-gray-700 text-4xl" aria-hidden="true">menu_book</span>
                <p className="text-sm text-gray-500">{entries.length === 0 ? '她还没有写下任何日记' : '该类型暂无日记'}</p>
              </div>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {filtered.map(e => {
                  const active = selected?.name === e.name
                  return (
                    <li key={e.name}>
                      <button
                        onClick={() => openEntry(e.name)}
                        className={`w-full text-left p-3 rounded-lg border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-blue)] ${
                          active
                            ? 'bg-[var(--accent-blue)]/10 border-[var(--accent-blue)]/40'
                            : 'bg-transparent border-transparent hover:bg-white/5 hover:border-gray-700/50'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded border ${TYPE_BADGE[e.type] || TYPE_BADGE.daily}`}>
                            {TYPE_LABEL[e.type] || '日记'}
                          </span>
                          <span className="text-[11px] font-mono text-gray-500 tabular-nums flex-shrink-0">{e.date}</span>
                        </div>
                        {e.preview && (
                          <p className="text-xs text-gray-400 line-clamp-2 min-w-0 break-words">{e.preview}</p>
                        )}
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>

        {/* 右栏：选中日记全文 */}
        <div className="flex-1 min-w-0 rounded-xl border border-gray-700/50 bg-[var(--header-bg)] flex flex-col min-h-0">
          {detailLoading ? (
            <p className="text-sm text-gray-500 p-6 animate-pulse">加载中…</p>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-2" aria-live="polite">
              <span className="material-symbols-outlined text-red-400/70 text-4xl" aria-hidden="true">error</span>
              <p className="text-sm text-red-400">{error}</p>
            </div>
          ) : !selected ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-3">
              <span className="material-symbols-outlined text-gray-700 text-6xl" aria-hidden="true">import_contacts</span>
              <p className="text-sm text-gray-500">选择左侧一篇日记开始阅读</p>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700/50 flex-shrink-0">
                <span className={`text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded border ${TYPE_BADGE[selected.type] || TYPE_BADGE.daily}`}>
                  {TYPE_LABEL[selected.type] || '日记'}
                </span>
                <span className="text-sm font-mono text-gray-400 tabular-nums">
                  {selected.date}
                  {selected.time && <span className="text-gray-600"> · {selected.time}</span>}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-5 [overscroll-behavior:contain]">
                <MarkdownRenderer content={selected.content} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
