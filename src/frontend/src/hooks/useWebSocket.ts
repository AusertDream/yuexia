import { useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import type { LogEntry } from '../types'

export function useLogSocket() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  useEffect(() => {
    const socket: Socket = io('/ws/logs', { reconnection: true, reconnectionDelay: 1000 })
    socket.on('log', (entry: LogEntry) => {
      setLogs(prev => [...prev.slice(-4999), entry])
    })
    return () => { socket.disconnect() }
  }, [])
  return logs
}

export function useEventSocket() {
  const [socket, setSocket] = useState<Socket | null>(null)
  useEffect(() => {
    const s = io('/ws/events', { reconnection: true, reconnectionDelay: 1000 })
    setSocket(s)
    return () => { s.disconnect() }
  }, [])
  return socket
}
