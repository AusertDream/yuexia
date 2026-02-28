import { create } from 'zustand'
import type { Session, ChatMessage } from '../types'
import * as sessApi from '../api/sessions'

let _msgIdCounter = 0
export function genMsgId(): string {
  return `msg-${Date.now()}-${++_msgIdCounter}`
}

/** 确保从后端加载的消息都有唯一 id */
function ensureIds(msgs: ChatMessage[]): ChatMessage[] {
  return msgs.map(m => m.id ? m : { ...m, id: genMsgId() })
}

interface ChatState {
  sessions: Session[]
  currentId: string
  messages: ChatMessage[]
  loading: boolean
  // 方法
  loadSessions: () => Promise<void>
  switchSession: (id: string) => Promise<void>
  createSession: () => Promise<void>
  deleteSession: (id: string) => Promise<void>
  setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void
  appendMessage: (msg: ChatMessage) => void
  updateLastAssistantMessage: (updater: (content: string) => string) => void
  updateLastAssistantTtsPath: (path: string) => void
  handleProactiveMessage: (text: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentId: '',
  messages: [],
  loading: false,

  loadSessions: async () => {
    set({ loading: true })
    try {
      const r = await sessApi.getSessions()
      const sessions = r.data.sessions
      const currentId = r.data.current_id
      set({ sessions, currentId, loading: false })
      // 如果有当前会话，加载消息
      if (currentId) {
        try {
          const sr = await sessApi.switchSession(currentId)
          set({ messages: ensureIds(sr.data.messages) })
        } catch (err) {
          console.error('加载当前会话消息失败:', err)
        }
      }
    } catch (err) {
      console.error('加载会话列表失败:', err)
      set({ loading: false })
    }
  },

  switchSession: async (id: string) => {
    try {
      const r = await sessApi.switchSession(id)
      set({ currentId: id, messages: ensureIds(r.data.messages) })
    } catch (err) {
      console.error('切换会话失败:', err)
    }
  },

  createSession: async () => {
    try {
      await sessApi.createSession()
      set({ messages: [] })
      await get().loadSessions()
    } catch (err) {
      console.error('创建会话失败:', err)
    }
  },

  deleteSession: async (id: string) => {
    try {
      await sessApi.deleteSession(id)
      const { currentId } = get()
      if (id === currentId) {
        set({ messages: [] })
      }
      await get().loadSessions()
    } catch (err) {
      console.error('删除会话失败:', err)
    }
  },

  setMessages: (messages) => {
    if (typeof messages === 'function') {
      set(state => ({ messages: messages(state.messages) }))
    } else {
      set({ messages })
    }
  },

  appendMessage: (msg) => {
    set(state => ({ messages: [...state.messages, msg] }))
  },

  updateLastAssistantMessage: (updater) => {
    set(state => {
      const copy = [...state.messages]
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === 'assistant') {
          copy[i] = { ...copy[i], content: updater(copy[i].content) }
          break
        }
      }
      return { messages: copy }
    })
  },

  updateLastAssistantTtsPath: (path: string) => {
    set(state => {
      const copy = [...state.messages]
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === 'assistant') {
          copy[i] = { ...copy[i], tts_path: path }
          break
        }
      }
      return { messages: copy }
    })
  },

  handleProactiveMessage: (text: string) => {
    set(state => ({
      messages: [...state.messages, { id: genMsgId(), role: 'assistant', content: text }],
    }))
  },
}))
