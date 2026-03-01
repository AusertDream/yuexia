import { create } from 'zustand'

interface SidebarState {
  collapsed: boolean
  setCollapsed: (collapsed: boolean | ((prev: boolean) => boolean)) => void
}

export const useSidebarStore = create<SidebarState>((set) => {
  // 从 localStorage 读取初始状态
  let initialCollapsed = false
  try {
    initialCollapsed = localStorage.getItem('sidebar-collapsed') === 'true'
  } catch {}

  return {
    collapsed: initialCollapsed,
    setCollapsed: (collapsed) => {
      const newValue = typeof collapsed === 'function'
        ? collapsed(useSidebarStore.getState().collapsed)
        : collapsed
      set({ collapsed: newValue })
      try {
        localStorage.setItem('sidebar-collapsed', String(newValue))
      } catch {}
    },
  }
})
