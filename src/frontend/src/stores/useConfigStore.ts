import { create } from 'zustand'
import { api } from '../api/client'

interface ConfigState {
  config: any
  loading: boolean
  saving: boolean
  // 方法
  loadConfig: () => Promise<void>
  saveConfig: () => Promise<boolean>
  setConfig: (config: any) => void
  updateField: (path: string, value: any) => void
  resetConfig: () => Promise<void>
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: null,
  loading: false,
  saving: false,

  loadConfig: async () => {
    set({ loading: true })
    try {
      const r = await api.get('/config')
      set({ config: r.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  saveConfig: async () => {
    const { config } = get()
    if (!config) return false
    set({ saving: true })
    try {
      await api.put('/config', config)
      set({ saving: false })
      return true
    } catch {
      set({ saving: false })
      return false
    }
  },

  setConfig: (config) => set({ config }),

  updateField: (path: string, value: any) => {
    const { config } = get()
    if (!config) return
    const copy = JSON.parse(JSON.stringify(config))
    const keys = path.split('.')
    let obj = copy
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {}
      obj = obj[keys[i]]
    }
    obj[keys[keys.length - 1]] = value
    set({ config: copy })
    // 主题色和深色模式立即应用
    if (path === 'general.accent_color') {
      document.documentElement.style.setProperty('--accent-blue', value)
    }
    if (path === 'general.dark_mode') {
      document.documentElement.classList.toggle('light', !value)
    }
  },

  resetConfig: async () => {
    await get().loadConfig()
  },
}))
