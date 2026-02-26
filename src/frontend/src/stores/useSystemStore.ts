import { create } from 'zustand'
import type { SystemStatus } from '../types'
import { api } from '../api/client'

interface SystemState {
  status: SystemStatus | null
  loading: boolean
  pollInterval: number
  pollTimer: number | null
  // 方法
  startPolling: () => void
  stopPolling: () => void
  setPollInterval: (ms: number) => void
  fetchStatus: () => Promise<void>
}

export const useSystemStore = create<SystemState>((set, get) => ({
  status: null,
  loading: false,
  pollInterval: 3000,
  pollTimer: null,

  fetchStatus: async () => {
    set({ loading: true })
    try {
      const r = await api.get<SystemStatus>('/system/status')
      set({ status: r.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  startPolling: () => {
    const state = get()
    // 避免重复启动
    if (state.pollTimer !== null) return

    // 立即获取一次
    state.fetchStatus()

    // 设置定时轮询
    const timer = window.setInterval(() => {
      get().fetchStatus()
    }, state.pollInterval)

    set({ pollTimer: timer })
  },

  stopPolling: () => {
    const { pollTimer } = get()
    if (pollTimer !== null) {
      clearInterval(pollTimer)
      set({ pollTimer: null })
    }
  },

  setPollInterval: (ms: number) => {
    const state = get()
    set({ pollInterval: ms })
    // 如果正在轮询，重启以应用新间隔
    if (state.pollTimer !== null) {
      state.stopPolling()
      // 延迟启动，确保 stopPolling 完成
      setTimeout(() => get().startPolling(), 0)
    }
  },
}))
