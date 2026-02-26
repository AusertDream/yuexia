import { useRef, useEffect, useState } from 'react'
import { useChatStream } from '../../hooks/useSSE'
import { useSocketStore, useChatStore } from '../../stores'

export default function ChatPanel() {
  const { sessions, currentId, messages, loadSessions, switchSession, createSession, deleteSession, setMessages } = useChatStore()
  const [input, setInput] = useState('')
  const [listening, setListening] = useState(false)
  const { sendMessage, streaming, cancel } = useChatStream()
  const bottomRef = useRef<HTMLDivElement>(null)
  const eventsConnected = useSocketStore(s => s.eventsConnected)

  useEffect(() => { loadSessions() }, [loadSessions])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    return () => { cancel() }
  }, [cancel])

  // TTS 自动播放
  useEffect(() => {
    if (!eventsConnected) return
    const handler = (d: { path: string }) => {
      if (!d.path) return
      const filename = d.path.replace(/\\/g, '/').split('/').pop()
      const url = '/audio/' + filename
      setMessages(prev => {
        const copy = [...prev]
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].role === 'assistant') { copy[i] = { ...copy[i], tts_path: url }; break }
        }
        return copy
      })
      new Audio(url).play().catch(() => {})
    }
    const store = useSocketStore.getState()
    store.onTtsDone(handler)
    return () => { store.offTtsDone(handler) }
  }, [eventsConnected, setMessages])

  const switchTo = (id: string) => { switchSession(id) }
  const newSession = () => { createSession() }

  const toggleVoice = () => {
    const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    if (!SR) return
    if (listening) return
    const rec = new SR()
    rec.lang = 'zh-CN'
    rec.interimResults = false
    rec.onresult = (e: any) => { setInput(prev => prev + e.results[0][0].transcript) }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    setListening(true)
    rec.start()
  }

  const playTts = (url: string) => { new Audio(url).play().catch(() => {}) }

  const send = () => {
    if (!input.trim() || streaming) return
    const text = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }, { role: 'assistant', content: '' }])

    sendMessage(text, chunk => {
      if (chunk.type === 'chunk') {
        setMessages(prev => {
          const copy = [...prev]
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: copy[copy.length - 1].content + chunk.text }
          return copy
        })
      } else if (chunk.type === 'error') {
        setMessages(prev => {
          const copy = [...prev]
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: `[错误] ${chunk.text || '服务器内部错误'}` }
          return copy
        })
      }
    }).catch(err => {
      if (err?.name !== 'AbortError') {
        setMessages(prev => {
          const copy = [...prev]
          if (copy.length > 0 && copy[copy.length - 1].role === 'assistant') {
            copy[copy.length - 1] = { ...copy[copy.length - 1], content: '[错误] 请求失败，请重试' }
          }
          return copy
        })
      }
    })
  }

  return (
    <div className="chat-panel rounded-xl flex flex-col overflow-hidden h-full shadow-[0_-5px_20px_rgba(0,0,0,0.3)]">
      {/* Tabs */}
      <div className="bg-[var(--panel-bg)] px-2 pt-2 border-b border-[var(--border-color)] flex items-center gap-2 overflow-x-auto custom-scrollbar">
        {sessions.map(s => (
          <button key={s.id} onClick={() => switchTo(s.id)}
            className={`px-4 py-2 text-xs font-medium rounded-t-lg flex items-center gap-2 ${s.id === currentId ? 'bg-[var(--tab-active)] text-[var(--text-primary)] border-t border-x border-[var(--border-color)]' : 'text-gray-400 hover:bg-[var(--tab-active)]/50'}`}>
            <span className={`w-2 h-2 rounded-full ${s.id === currentId ? 'bg-green-500' : 'bg-gray-500'}`} />
            {s.title?.slice(0, 15) || '新对话'}
            {/* 删除会话按钮 */}
            <span className="ml-1 hover:text-red-400 text-gray-500 cursor-pointer" onClick={e => {
              e.stopPropagation()
              deleteSession(s.id)
            }}>&times;</span>
          </button>
        ))}
        <button onClick={newSession} className="ml-1 mb-1 self-center p-1 text-gray-500 hover:text-[var(--accent-blue)]">
          <span className="material-symbols-outlined text-[18px]">add</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 bg-[var(--header-bg)]/60 p-4 overflow-y-auto custom-scrollbar flex flex-col gap-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-[var(--accent-blue)]/10 mr-3 flex items-center justify-center border border-[var(--accent-blue)]/30 flex-shrink-0">
                <span className="material-symbols-outlined text-sm text-[var(--accent-blue)]">smart_toy</span>
              </div>
            )}
            <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm ${m.role === 'user' ? 'bg-[var(--bubble-user)] text-gray-200 rounded-tr-sm border border-gray-700' : 'bg-[var(--bubble-ai)] text-gray-300 rounded-tl-sm border border-gray-800'}`}>
              {m.content}
              {m.role === 'assistant' && streaming && i === messages.length - 1 && (
                <span className="inline-block w-1.5 h-3 bg-[var(--accent-blue)] ml-1 animate-pulse" />
              )}
              {m.role === 'assistant' && m.tts_path && (
                <button onClick={() => playTts(m.tts_path!)} className="ml-2 text-[var(--accent-blue)] hover:text-cyan-300 align-middle">
                  <span className="material-symbols-outlined text-[16px]">volume_up</span>
                </button>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 bg-[var(--panel-bg)] border-t border-[var(--border-color)]">
        <div className="relative flex items-center gap-2 bg-[var(--panel-bg-alt)] border border-[var(--border-color)] rounded-xl p-2 focus-within:ring-1 focus-within:ring-[var(--accent-blue)]">
          <textarea
            className="flex-1 bg-transparent border-none p-2 text-sm text-gray-200 placeholder-gray-500 focus:ring-0 focus:outline-none resize-none"
            placeholder="发送消息给月下..."
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          />
          {'webkitSpeechRecognition' in window && (
            <button onClick={toggleVoice}
              className={`p-2 rounded-lg transition-colors ${listening ? 'bg-red-500/20 text-red-400 animate-pulse' : 'text-gray-400 hover:text-[var(--accent-blue)]'}`}>
              <span className="material-symbols-outlined text-[20px]">mic</span>
            </button>
          )}
          <button onClick={send} disabled={streaming}
            className="p-2 bg-[var(--accent-blue)] text-black rounded-lg hover:bg-cyan-300 transition-colors shadow-[0_0_10px_rgba(0,240,255,0.3)] disabled:opacity-50">
            <span className="material-symbols-outlined text-[20px]">send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
