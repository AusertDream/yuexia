import { NavLink } from 'react-router-dom'
import { useSocketStore, useSidebarStore } from '../../stores'

const NAV = [
  { to: '/', icon: 'dashboard', label: '仪表盘' },
  { to: '/config', icon: 'settings_applications', label: '系统配置' },
  { to: '/perception', icon: 'visibility', label: '感知监控' },
  { to: '/logs', icon: 'terminal', label: '系统日志' },
]

export default function Sidebar() {
  const eventsConnected = useSocketStore(s => s.eventsConnected)
  const collapsed = useSidebarStore(s => s.collapsed)
  const setCollapsed = useSidebarStore(s => s.setCollapsed)

  return (
    <nav className={`${collapsed ? 'w-20' : 'w-20 lg:w-64'} flex-shrink-0 glass-panel border-r border-[var(--border-color)] flex flex-col justify-between py-6 z-20 transition-all duration-300`}>
      <div className="flex flex-col gap-2">
        <div className={`px-6 mb-8 ${collapsed ? 'hidden' : 'hidden lg:block'}`}>
          <h1 className="text-xl font-bold tracking-wider text-[var(--text-primary)]">
            YUE<span className="text-[var(--accent-blue)]">XIA</span>
          </h1>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">数字人核心</p>
        </div>
        {NAV.map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            className={({ isActive }) =>
              `nav-item flex items-center gap-4 px-4 lg:px-6 py-3 text-gray-400 hover:text-white group ${isActive ? 'active' : ''}`
            }
          >
            <span className="material-symbols-outlined group-hover:scale-110 transition-transform">{n.icon}</span>
            <span className={`${collapsed ? 'hidden' : 'hidden lg:block'} text-sm font-medium`}>{n.label}</span>
          </NavLink>
        ))}
      </div>
      <div>
        <button
          onClick={() => setCollapsed(v => !v)}
          className="w-full flex items-center justify-center py-2 text-gray-500 hover:text-[var(--accent-blue)] transition-colors"
        >
          <span className="material-symbols-outlined">
            {collapsed ? 'chevron_right' : 'chevron_left'}
          </span>
        </button>
        <div className={collapsed ? 'px-2' : 'px-4 lg:px-6'}>
          <div className="glass-panel p-3 rounded-lg border border-gray-700/50">
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${eventsConnected ? 'bg-green-500 shadow-[0_0_8px_rgba(16,185,129,0.6)] animate-pulse' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`} />
              <span className={`${collapsed ? 'hidden' : 'hidden lg:block'} text-xs font-mono ${eventsConnected ? 'text-green-400' : 'text-red-400'}`}>
                {eventsConnected ? '系统在线' : '连接断开'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
