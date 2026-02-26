import { create } from 'zustand'
import { io, Socket } from 'socket.io-client'
import type { LogEntry } from '../types'

// 事件类型定义
type TtsDoneHandler = (data: { path: string }) => void
type AsrResultHandler = (data: { text: string }) => void
type UserMessageHandler = (data: { text: string }) => void
type AiMessageHandler = (data: { text: string }) => void
type ExpressionHandler = (data: { emotion: string }) => void

interface SocketState {
  // 连接实例
  eventsSocket: Socket | null
  logsSocket: Socket | null
  // 连接状态
  eventsConnected: boolean
  logsConnected: boolean
  // 日志缓存
  logs: LogEntry[]
  // 连接管理
  connect: () => void
  disconnect: () => void
  // 事件监听方法
  onTtsDone: (handler: TtsDoneHandler) => void
  offTtsDone: (handler: TtsDoneHandler) => void
  onAsrResult: (handler: AsrResultHandler) => void
  offAsrResult: (handler: AsrResultHandler) => void
  onUserMessage: (handler: UserMessageHandler) => void
  offUserMessage: (handler: UserMessageHandler) => void
  onAiMessage: (handler: AiMessageHandler) => void
  offAiMessage: (handler: AiMessageHandler) => void
  onExpression: (handler: ExpressionHandler) => void
  offExpression: (handler: ExpressionHandler) => void
  // 清除日志
  clearLogs: () => void
}

export const useSocketStore = create<SocketState>((set, get) => ({
  eventsSocket: null,
  logsSocket: null,
  eventsConnected: false,
  logsConnected: false,
  logs: [],

  connect: () => {
    const state = get()
    // 避免重复连接
    if (state.eventsSocket || state.logsSocket) return

    // 创建 events socket
    const eventsSocket = io('/ws/events', {
      reconnection: true,
      reconnectionDelay: 1000,
    })
    eventsSocket.on('connect', () => set({ eventsConnected: true }))
    eventsSocket.on('disconnect', () => set({ eventsConnected: false }))

    // 创建 logs socket
    const logsSocket = io('/ws/logs', {
      reconnection: true,
      reconnectionDelay: 1000,
    })
    logsSocket.on('connect', () => set({ logsConnected: true }))
    logsSocket.on('disconnect', () => set({ logsConnected: false }))
    // 日志事件处理
    logsSocket.on('log', (entry: LogEntry) => {
      set(state => ({ logs: [...state.logs.slice(-4999), entry] }))
    })

    set({ eventsSocket, logsSocket })
  },

  disconnect: () => {
    const { eventsSocket, logsSocket } = get()
    eventsSocket?.disconnect()
    logsSocket?.disconnect()
    set({
      eventsSocket: null,
      logsSocket: null,
      eventsConnected: false,
      logsConnected: false,
    })
  },

  // TTS 完成事件
  onTtsDone: (handler) => {
    get().eventsSocket?.on('tts_done', handler)
  },
  offTtsDone: (handler) => {
    get().eventsSocket?.off('tts_done', handler)
  },

  // ASR 识别结果
  onAsrResult: (handler) => {
    get().eventsSocket?.on('asr_result', handler)
  },
  offAsrResult: (handler) => {
    get().eventsSocket?.off('asr_result', handler)
  },

  // 用户消息
  onUserMessage: (handler) => {
    get().eventsSocket?.on('user_message', handler)
  },
  offUserMessage: (handler) => {
    get().eventsSocket?.off('user_message', handler)
  },

  // AI 消息
  onAiMessage: (handler) => {
    get().eventsSocket?.on('ai_message', handler)
  },
  offAiMessage: (handler) => {
    get().eventsSocket?.off('ai_message', handler)
  },

  // 表情事件
  onExpression: (handler) => {
    get().eventsSocket?.on('expression', handler)
  },
  offExpression: (handler) => {
    get().eventsSocket?.off('expression', handler)
  },

  clearLogs: () => set({ logs: [] }),
}))
