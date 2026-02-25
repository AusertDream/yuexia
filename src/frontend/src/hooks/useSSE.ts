import { useCallback, useRef, useState } from 'react'
import type { StreamChunk } from '../types'

export function useChatStream() {
  const [streaming, setStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  const sendMessage = useCallback(async (text: string, onChunk: (c: StreamChunk) => void) => {
    cancel()
    const controller = new AbortController()
    abortRef.current = controller
    setStreaming(true)
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        onChunk({ type: 'error', text: errBody.error || `HTTP ${res.status}` })
        return
      }
      if (!res.body) {
        onChunk({ type: 'error', text: '浏览器不支持流式响应' })
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              onChunk(JSON.parse(line.slice(6)))
            } catch {
              // 忽略畸形 JSON 行
            }
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        onChunk({ type: 'error', text: (e as Error).message || '网络错误' })
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      setStreaming(false)
    }
  }, [cancel])

  return { sendMessage, streaming, cancel }
}
