import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import DashboardPage from './pages/DashboardPage'
import ConfigPage from './pages/ConfigPage'
import PerceptionPage from './pages/PerceptionPage'
import LogsPage from './pages/LogsPage'
import { useSocketStore, useSidebarStore } from './stores'
import ToastContainer from './components/ui/Toast'

function AppContent() {
  const location = useLocation()
  const isDashboard = location.pathname === '/'
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const collapsed = useSidebarStore(s => s.collapsed)

  const [locked, setLocked] = useState(() => {
    try { return localStorage.getItem('live2d-locked') === 'true' } catch { return false }
  })

  useEffect(() => {
    try { localStorage.setItem('live2d-locked', String(locked)) } catch {}
  }, [locked])

  const handleIframeLoad = () => {
    iframeRef.current?.contentWindow?.postMessage({ type: 'set-lock', locked }, '*')
  }

  useEffect(() => {
    iframeRef.current?.contentWindow?.postMessage({ type: 'set-lock', locked }, '*')
  }, [locked])

  const sidebarWidth = collapsed ? '80px' : (typeof window !== 'undefined' && window.innerWidth >= 1024 ? '256px' : '80px')

  return (
    <div className="flex-1 flex overflow-hidden relative">
      <Sidebar />
      {/* 持久化 Live2D 层 - 始终挂载，仅在仪表盘可见 */}
      <div
        className={`absolute top-0 bottom-0 z-[5] left-20 lg:left-64 right-0 ${isDashboard ? '' : 'invisible'}`}
      >
        <iframe
          ref={iframeRef}
          src="/live2d/index.html"
          className="w-full h-full border-0"
          title="Live2D"
          onLoad={handleIframeLoad}
        />
      </div>
      {/* 主内容区 - 非仪表盘时有背景色遮挡 iframe */}
      <main className={`flex-1 overflow-hidden relative ${isDashboard ? 'pointer-events-none' : 'z-10 bg-[var(--bg-color)]'}`}>
        <div className={isDashboard ? 'pointer-events-auto h-full' : 'h-full'}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/perception" element={<PerceptionPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </div>
      </main>
      {/* Live2D 锁定按钮 - 固定在右上角 */}
      {isDashboard && (
        <button
          onClick={() => setLocked(v => !v)}
          className="fixed top-4 right-[calc(min(420px,35vw)+2rem)] z-30 p-2 rounded-lg backdrop-blur-sm border transition-colors"
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
      )}
    </div>
  )
}

export default function App() {
  useEffect(() => {
    useSocketStore.getState().connect()
    return () => {
      useSocketStore.getState().disconnect()
    }
  }, [])

  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col antialiased">
        <div className="h-8 bg-[var(--header-bg)] flex items-center justify-between px-4 border-b border-gray-800 select-none">
          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] font-mono">
            <span className="material-symbols-outlined text-[16px] text-[#00f0ff]">smart_toy</span>
            <span>月下协议 // 控制中心 v1.0.5-web</span>
          </div>
        </div>
        <AppContent />
      </div>
      <ToastContainer />
    </BrowserRouter>
  )
}
