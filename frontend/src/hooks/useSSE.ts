import { useCallback, useState } from 'react'
import type { StreamChunk } from '../types'

export function useChatStream() {
  const [streaming, setStreaming] = useState(false)

  const sendMessage = useCallback(async (text: string, onChunk: (c: StreamChunk) => void) => {
    setStreaming(true)
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      const reader = res.body!.getReader()
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
            onChunk(JSON.parse(line.slice(6)))
          }
        }
      }
    } finally {
      setStreaming(false)
    }
  }, [])

  return { sendMessage, streaming }
}
