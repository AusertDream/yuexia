import { api } from './client'
import type { Session, ChatMessage } from '../types'

export const getSessions = () => api.get<{ sessions: Session[]; current_id: string }>('/sessions')
export const createSession = () => api.post<{ session_id: string }>('/sessions')
export const switchSession = (id: string) => api.get<{ session_id: string; messages: ChatMessage[] }>(`/sessions/${id}`)
export const renameSession = (id: string, title: string) => api.put(`/sessions/${id}`, { title })
export const deleteSession = (id: string) => api.delete(`/sessions/${id}`)
