import { useToastStore } from '../../stores/useToastStore'
import type { ToastType } from '../../stores/useToastStore'

const ICONS: Record<ToastType, string> = {
  success: 'check_circle',
  error: 'error',
  warning: 'warning',
  info: 'info',
}

const ACCENT: Record<ToastType, string> = {
  success: 'var(--success)',
  error: 'var(--error)',
  warning: 'var(--warning)',
  info: 'var(--accent-blue)',
}

export default function ToastContainer() {
  const toasts = useToastStore(s => s.toasts)
  const removeToast = useToastStore(s => s.removeToast)

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl backdrop-blur-sm border shadow-lg min-w-[280px] max-w-[400px] bg-[var(--panel-bg)]/90 border-[var(--border-color)] text-[var(--text-primary)]"
          style={{
            animation: t.removing ? 'toast-out 0.3s ease forwards' : 'toast-in 0.3s ease',
            borderColor: `color-mix(in srgb, ${ACCENT[t.type]} 20%, transparent)`,
            boxShadow: `0 4px 24px rgba(0,0,0,0.3), inset 0 0 0 1px color-mix(in srgb, ${ACCENT[t.type]} 10%, transparent)`,
          }}
          onAnimationEnd={() => { if (t.removing) removeToast(t.id) }}
        >
          <span
            className="material-symbols-outlined text-[20px] flex-shrink-0"
            style={{ color: ACCENT[t.type] }}
          >
            {ICONS[t.type]}
          </span>
          <span className="text-sm flex-1">{t.message}</span>
          <button
            onClick={() => removeToast(t.id)}
            className="text-gray-400 hover:text-white transition-colors flex-shrink-0"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      ))}
    </div>
  )
}
