import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import DashboardPage from './pages/DashboardPage'
import ConfigPage from './pages/ConfigPage'
import PerceptionPage from './pages/PerceptionPage'
import LogsPage from './pages/LogsPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col antialiased">
        <div className="h-8 bg-[#0a0c10] flex items-center justify-between px-4 border-b border-gray-800 select-none">
          <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
            <span className="material-symbols-outlined text-[16px] text-[#00f0ff]">smart_toy</span>
            <span>月下协议 // 控制中心 v1.0.5-web</span>
          </div>
        </div>
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-hidden">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="/perception" element={<PerceptionPage />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
