/**
 * Live2D iframe 通信桥接模块 —— 模块级单例。
 * App.tsx 在 iframe onLoad 时注册 frameWindow，后续所有 Live2D 指令通过此模块收发。
 */

let frameWindow: Window | null = null
let speaking = false

window.addEventListener('message', (e: MessageEvent) => {
  if (!e.data || typeof e.data !== 'object') return
  if (e.data.type === 'live2d-speak-state' && e.origin === window.location.origin) {
    speaking = Boolean(e.data.playing)
  }
})

export function registerLive2DFrame(win: Window | null): void {
  frameWindow = win
}

export function live2dSpeak(url: string, emotion?: string): boolean {
  if (!frameWindow) return false
  frameWindow.postMessage({ type: 'speak', url, emotion }, window.location.origin)
  return true
}

export function live2dSetExpression(emotion: string): void {
  if (!frameWindow) return
  frameWindow.postMessage({ type: 'expression', emotion }, window.location.origin)
}

export function isLive2DSpeaking(): boolean {
  return speaking
}
