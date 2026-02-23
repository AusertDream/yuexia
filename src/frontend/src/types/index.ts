export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  tts_path?: string
}

export interface Session {
  id: string
  title: string
  updated_at: number
}

export interface StreamChunk {
  type: 'chunk' | 'end' | 'error'
  text: string
  emotion?: string
}

export interface LogEntry {
  time: string
  level: string
  module: string
  message: string
}

export interface SystemStatus {
  cpu_percent: number
  ram_used: number
  ram_total: number
  gpu: { name: string; mem_used: number; mem_total: number; load: number } | null
  services_ready: boolean
  loading_status: Record<string, string>
  inference_speed: number
}
