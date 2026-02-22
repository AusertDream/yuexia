import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/', icon: 'dashboard', label: '仪表盘' },
  { to: '/config', icon: 'settings_applications', label: '系统配置' },
  { to: '/perception', icon: 'visibility', label: '感知监控' },
  { to: '/logs', icon: 'terminal', label: '系统日志' },
]

export default function Sidebar() {
  return (
    <nav className="w-20 lg:w-64 flex-shrink-0 glass-panel border-r border-gray-800 flex flex-col justify-between py-6 z-20">
      <div className="flex flex-col gap-2">
        <div className="px-6 mb-8 hidden lg:block">
          <h1 className="text-xl font-bold tracking-wider text-white">
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
            <span className="hidden lg:block text-sm font-medium">{n.label}</span>
          </NavLink>
        ))}
      </div>
      <div className="px-4 lg:px-6">
        <div className="glass-panel p-3 rounded-lg border border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(16,185,129,0.6)] animate-pulse" />
            <span className="hidden lg:block text-xs font-mono text-green-400">系统在线</span>
          </div>
        </div>
      </div>
    </nav>
  )
}
