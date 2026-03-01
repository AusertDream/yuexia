import { create } from 'zustand'
import { useEffect } from 'react'
import type { SystemStatus } from '../types'
import { api } from '../api/client'

interface SystemState {
  status: SystemStatus | null
  loading: boolean
  pollInterval: number
  pollTimer: number | null
  subscriberCount: number
  // 方法
  subscribe: () => void
  unsubscribe: () => void
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
  subscriberCount: 0,

  fetchStatus: async () => {
    set({ loading: true })
    try {
      const r = await api.get<SystemStatus>('/system/status')
      set({ status: r.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  subscribe: () => {
    const count = get().subscriberCount + 1
    set({ subscriberCount: count })
    if (count === 1) get().startPolling()
  },

  unsubscribe: () => {
    const count = Math.max(0, get().subscriberCount - 1)
    set({ subscriberCount: count })
    if (count === 0) get().stopPolling()
  },

  startPolling: () => {
    const state = get()
    if (state.pollTimer !== null) return
    state.fetchStatus()
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
    if (state.pollTimer !== null) {
      state.stopPolling()
      setTimeout(() => get().startPolling(), 0)
    }
  },
}))

/** 组件级 hook：挂载时订阅轮询，卸载时取消 */
export function useSystemStatus() {
  const status = useSystemStore(s => s.status)
  useEffect(() => {
    useSystemStore.getState().subscribe()
    return () => useSystemStore.getState().unsubscribe()
  }, [])
  return status
}
