import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastItem {
  id: string
  message: string
  type: ToastType
  duration: number
  removing?: boolean
}

interface ToastState {
  toasts: ToastItem[]
  addToast: (message: string, type?: ToastType, duration?: number) => void
  removeToast: (id: string) => void
  markRemoving: (id: string) => void
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],

  addToast: (message, type = 'info', duration = 3000) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    set(s => ({ toasts: [...s.toasts, { id, message, type, duration }] }))
    if (duration > 0) {
      setTimeout(() => get().markRemoving(id), duration)
    }
  },

  markRemoving: (id) => {
    set(s => ({
      toasts: s.toasts.map(t => t.id === id ? { ...t, removing: true } : t)
    }))
  },

  removeToast: (id) => {
    set(s => ({ toasts: s.toasts.filter(t => t.id !== id) }))
  },
}))

export const toast = {
  success: (msg: string, duration?: number) => useToastStore.getState().addToast(msg, 'success', duration),
  error: (msg: string, duration?: number) => useToastStore.getState().addToast(msg, 'error', duration),
  warning: (msg: string, duration?: number) => useToastStore.getState().addToast(msg, 'warning', duration),
  info: (msg: string, duration?: number) => useToastStore.getState().addToast(msg, 'info', duration),
}
