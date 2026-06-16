import { useRef, useEffect, useState, useCallback } from 'react'
import { useChatStream } from '../../hooks/useSSE'
import { useSocketStore, useChatStore } from '../../stores'
import { genMsgId } from '../../stores/useChatStore'
import MarkdownRenderer from './MarkdownRenderer'
import { live2dSpeak, isLive2DSpeaking } from '../../lib/live2dBridge'

function getInitialConversationMode(): boolean {
  try {
    return localStorage.getItem('yuexia-conversation-mode') === 'true'
  } catch {
    return false
  }
}

export default function ChatPanel() {
  const { sessions, currentId, messages, loadSessions, switchSession, createSession, deleteSession, setMessages } = useChatStore()
  const [input, setInput] = useState('')
  const [listening, setListening] = useState(false)
  const [conversationMode, setConversationMode] = useState(getInitialConversationMode)
  const { sendMessage, streaming, cancel } = useChatStream()
  const bottomRef = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const eventsConnected = useSocketStore(s => s.eventsConnected)

  // 用 ref 保存 streaming 和 conversationMode，避免 asr_result effect 的过期闭包
  const streamingRef = useRef(streaming)
  streamingRef.current = streaming
  const conversationModeRef = useRef(conversationMode)
  conversationModeRef.current = conversationMode
  // 用 ref 跟踪当前输入框内容，供 asr_result 处理器在事件回调中直接读取（避免在 state updater 内做副作用）
  const inputRef = useRef(input)
  inputRef.current = input

  // 持久化 conversationMode
  useEffect(() => {
    try {
      localStorage.setItem('yuexia-conversation-mode', String(conversationMode))
    } catch { /* ignore */ }
  }, [conversationMode])

  useEffect(() => { loadSessions() }, [loadSessions])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    return () => { cancel() }
  }, [cancel])

  // ASR 识别结果监听
  useEffect(() => {
    if (!eventsConnected) return
    const handler = (d: { text: string }) => {
      if (!d.text) return
      if (!conversationModeRef.current) {
        // 普通模式：追加到输入框
        setInput(prev => prev + d.text)
        return
      }
      // 对话模式
      if (isLive2DSpeaking()) return // 避免回声
      if (streamingRef.current) {
        setInput(prev => prev + d.text)
        return
      }
      // 未在 streaming：取当前输入框内容合并后自动发送
      const merged = (inputRef.current + d.text).trim()
      if (!merged) return // 空白不发送
      setInput('')
      sendText(merged)
    }
    const store = useSocketStore.getState()
    store.onAsrResult(handler)
    return () => { store.offAsrResult(handler) }
  }, [eventsConnected])

  const switchTo = (id: string) => { switchSession(id) }
  const newSession = () => { createSession() }

  const toggleVoice = async () => {
    try {
      if (!listening) {
        // 启动 ASR
        const response = await fetch('/api/asr/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device: null }) // 使用默认麦克风
        })
        if (!response.ok) {
          const error = await response.json()
          console.error('启动ASR失败:', error)
          return
        }
        setListening(true)
      } else {
        // 停止 ASR
        const response = await fetch('/api/asr/stop', {
          method: 'POST'
        })
        if (!response.ok) {
          const error = await response.json()
          console.error('停止ASR失败:', error)
          return
        }
        setListening(false)
      }
    } catch (err) {
      console.error('ASR操作失败:', err)
    }
  }

  const playTts = (url: string) => {
    if (live2dSpeak(url)) return

    // Live2D 不可用时回退到 HTML Audio
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }

    const audio = new Audio(url)
    audioRef.current = audio

    audio.play().catch(() => {})

    audio.onended = () => {
      if (audioRef.current === audio) {
        audioRef.current = null
      }
    }
  }

  const sendText = useCallback((text: string) => {
    if (!text.trim() || streamingRef.current) return
    const trimmed = text.trim()
    setMessages(prev => [...prev, { id: genMsgId(), role: 'user', content: trimmed }, { id: genMsgId(), role: 'assistant', content: '' }])

    sendMessage(trimmed, chunk => {
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
  }, [sendMessage, setMessages])

  const send = useCallback(() => {
    if (!input.trim() || streaming) return
    const text = input.trim()
    setInput('')
    sendText(text)
  }, [input, streaming, sendText])

  return (
    <div className="glass-chat rounded-2xl flex flex-col overflow-hidden h-full shadow-[0_-5px_20px_rgba(0,0,0,0.3)]" style={{ willChange: 'transform' }}>
      {/* Tabs */}
      <div className="bg-white/[0.08] px-2 pt-2 border-b border-[var(--glass-chat-border)] flex items-center gap-2 overflow-x-auto custom-scrollbar">
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
        <button onClick={newSession} className="ml-1 self-center p-1 text-gray-500 hover:text-[var(--accent-blue)]">
          <span className="material-symbols-outlined text-[18px]">add</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 bg-transparent p-4 overflow-y-auto custom-scrollbar flex flex-col gap-4">
        {messages.map((m, i) => (
          m.role === 'system' ? (
            <div key={m.id} className="text-center py-1">
              <span className="text-xs text-gray-500">{m.content}</span>
            </div>
          ) : (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-[var(--accent-blue)]/10 mr-3 flex items-center justify-center border border-[var(--accent-blue)]/30 flex-shrink-0">
                <span className="material-symbols-outlined text-sm text-[var(--accent-blue)]">smart_toy</span>
              </div>
            )}
            <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm ${m.role === 'user' ? 'bg-[var(--bubble-user)] text-gray-200 rounded-tr-sm border border-gray-700' : 'bg-black/20 text-gray-300 rounded-tl-sm border border-gray-800'}`} style={m.role === 'assistant' ? { textShadow: '0 1px 2px rgba(0,0,0,0.3)' } : undefined}>
              {m.role === 'assistant' ? (
                <MarkdownRenderer content={m.content} />
              ) : (
                <span className="whitespace-pre-wrap">{m.content}</span>
              )}
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
          )
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 bg-black/10 border-t border-[var(--border-color)]">
        <div className="relative flex items-center gap-2 bg-white/3 border border-[var(--border-color)] rounded-xl p-2 focus-within:ring-1 focus-within:ring-[var(--accent-blue)]">
          <textarea
            className="flex-1 bg-transparent border-none p-2 text-sm text-gray-200 placeholder-gray-500 focus:ring-0 focus:outline-none resize-none"
            placeholder="发送消息给月下..."
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          />
          <button onClick={() => setConversationMode(v => !v)}
            className={`p-2 rounded-lg transition-colors ${conversationMode ? 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue)]' : 'text-gray-400 hover:text-[var(--accent-blue)]'}`}
            title={conversationMode ? '对话模式：说完自动发送' : '对话模式已关闭'}>
            <span className="material-symbols-outlined text-[20px]">voice_chat</span>
          </button>
          <button onClick={toggleVoice}
            className={`p-2 rounded-lg transition-colors ${listening ? 'bg-red-500/20 text-red-400 animate-pulse' : 'text-gray-400 hover:text-[var(--accent-blue)]'}`}>
            <span className="material-symbols-outlined text-[20px]">mic</span>
          </button>
          <button onClick={send} disabled={streaming}
            className="p-2 bg-[var(--accent-blue)] text-black rounded-lg hover:bg-cyan-300 interactive-hover disabled:opacity-50">
            <span className="material-symbols-outlined text-[20px]">send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
