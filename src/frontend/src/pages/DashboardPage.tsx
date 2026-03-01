import { useEffect, useState } from 'react'
import ChatPanel from '../components/chat/ChatPanel'
import { api } from '../api/client'

const orbs = [
  { size: 300, x: '15%', y: '20%', color: 'rgba(80, 60, 200, 0.25)', anim: 'orb-float-1', dur: '25s' },
  { size: 220, x: '70%', y: '60%', color: 'rgba(40, 100, 220, 0.2)', anim: 'orb-float-2', dur: '30s' },
  { size: 260, x: '45%', y: '75%', color: 'rgba(120, 50, 180, 0.2)', anim: 'orb-float-3', dur: '22s' },
  { size: 180, x: '80%', y: '15%', color: 'rgba(60, 80, 210, 0.18)', anim: 'orb-float-2', dur: '28s' },
  { size: 200, x: '25%', y: '50%', color: 'rgba(100, 40, 200, 0.15)', anim: 'orb-float-1', dur: '35s' },
]

export default function DashboardPage() {
  const [bgUrl, setBgUrl] = useState<string | null>(null)

  useEffect(() => {
    api.get('/config/chat-bg').then(r => {
      if (r.data?.exists && r.data.url) setBgUrl(r.data.url)
    }).catch(() => {})
  }, [])

  // 监听自定义事件，配置页上传/删除背景后同步刷新
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      setBgUrl(detail?.url || null)
    }
    window.addEventListener('chat-bg-changed', handler)
    return () => window.removeEventListener('chat-bg-changed', handler)
  }, [])

  return (
    <div className="relative h-full w-full overflow-hidden">
      {/* Background: custom image or aurora gradient */}
      {bgUrl ? (
        <div
          className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: `url(${bgUrl})` }}
        />
      ) : (
        <div className="absolute inset-0 z-0 aurora-bg">
          {orbs.map((o, i) => (
            <div
              key={i}
              className="absolute rounded-full"
              style={{
                width: o.size,
                height: o.size,
                left: o.x,
                top: o.y,
                background: `radial-gradient(circle, ${o.color} 0%, transparent 70%)`,
                filter: 'blur(40px)',
                animation: `${o.anim} ${o.dur} ease-in-out infinite`,
                willChange: 'transform',
              }}
            />
          ))}
        </div>
      )}
      <div
        className="absolute right-6 top-6 bottom-6 z-10"
        style={{ width: 'min(420px, 35vw)', minWidth: '320px' }}
      >
        <ChatPanel />
      </div>
    </div>
  )
}
