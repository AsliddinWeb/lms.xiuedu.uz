import { apiClient } from './client'

export type NotificationEventType =
  | 'exam.published'
  | 'exam.graded'
  | 'appeal.response'
  | 'live.scheduled'
  | 'live.starting'
  | 'system'

export interface NotificationPublic {
  id: number
  user_id: number
  event_type: NotificationEventType | string
  title: string
  body: string | null
  action_url: string | null
  data: Record<string, unknown> | null
  read_at: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedNotifications {
  items: NotificationPublic[]
  total: number
  unread_count: number
}

export const notificationsApi = {
  async list(params: { unread_only?: boolean; page?: number; page_size?: number } = {}): Promise<PaginatedNotifications> {
    const { data } = await apiClient.get<PaginatedNotifications>('/notifications', { params })
    return data
  },

  async unreadCount(): Promise<number> {
    const { data } = await apiClient.get<{ count: number }>('/notifications/unread-count')
    return data.count
  },

  async markRead(id: number): Promise<NotificationPublic> {
    return (await apiClient.post<NotificationPublic>(`/notifications/${id}/read`)).data
  },

  async markAllRead(): Promise<number> {
    const { data } = await apiClient.post<{ marked: number }>('/notifications/read-all')
    return data.marked
  },
}
