/**
 * Chat API klient — Phase 11b.
 *
 * Endpointlar `/api/v1/chat/*` ostida. WebSocket `?token=...` query param bilan.
 */
import { apiClient } from './client'

export type ConversationType = 'direct' | 'group' | 'course'

export interface ConversationPublic {
  id: number
  type: ConversationType
  title: string | null
  course_id: number | null
  created_by: number | null
  last_message_at: string | null
  is_archived: boolean
  created_at: string
  unread_count: number
  last_message_preview: string | null
  member_ids: number[]
  member_names: Record<number, string>
}

export interface MessagePublic {
  id: number
  conversation_id: number
  sender_id: number | null
  sender_name: string | null
  body: string | null
  attachment_url: string | null
  attachment_mime: string | null
  attachment_size: number | null
  reply_to_id: number | null
  edited_at: string | null
  deleted_at: string | null
  created_at: string
}

export interface PaginatedConversations {
  items: ConversationPublic[]
  total: number
}

export interface PaginatedMessages {
  items: MessagePublic[]
  has_more: boolean
}

export const chatApi = {
  async listConversations(params: {
    include_archived?: boolean
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedConversations> {
    const { data } = await apiClient.get<PaginatedConversations>(
      '/chat/conversations',
      { params },
    )
    return data
  },

  async getConversation(id: number): Promise<ConversationPublic> {
    return (await apiClient.get<ConversationPublic>(`/chat/conversations/${id}`)).data
  },

  async openDirect(peerUserId: number): Promise<ConversationPublic> {
    const { data } = await apiClient.post<ConversationPublic>(
      '/chat/conversations/direct',
      { peer_user_id: peerUserId },
    )
    return data
  },

  async createGroup(payload: {
    title: string
    member_ids: number[]
    course_id?: number | null
  }): Promise<ConversationPublic> {
    const { data } = await apiClient.post<ConversationPublic>(
      '/chat/conversations/group',
      payload,
    )
    return data
  },

  async addMembers(
    conversationId: number,
    userIds: number[],
  ): Promise<ConversationPublic> {
    const { data } = await apiClient.post<ConversationPublic>(
      `/chat/conversations/${conversationId}/members`,
      { user_ids: userIds },
    )
    return data
  },

  async removeMember(conversationId: number, targetUserId: number): Promise<void> {
    await apiClient.delete(
      `/chat/conversations/${conversationId}/members/${targetUserId}`,
    )
  },

  async markRead(
    conversationId: number,
    lastMessageId?: number,
  ): Promise<ConversationPublic> {
    const { data } = await apiClient.post<ConversationPublic>(
      `/chat/conversations/${conversationId}/read`,
      { last_message_id: lastMessageId ?? null },
    )
    return data
  },

  async listMessages(
    conversationId: number,
    params: { before_id?: number; limit?: number } = {},
  ): Promise<PaginatedMessages> {
    const { data } = await apiClient.get<PaginatedMessages>(
      `/chat/conversations/${conversationId}/messages`,
      { params },
    )
    return data
  },

  async sendMessage(
    conversationId: number,
    payload: {
      body?: string | null
      attachment_url?: string | null
      attachment_mime?: string | null
      attachment_size?: number | null
      reply_to_id?: number | null
    },
  ): Promise<MessagePublic> {
    const { data } = await apiClient.post<MessagePublic>(
      `/chat/conversations/${conversationId}/messages`,
      payload,
    )
    return data
  },

  async editMessage(messageId: number, body: string): Promise<MessagePublic> {
    const { data } = await apiClient.patch<MessagePublic>(
      `/chat/messages/${messageId}`,
      { body },
    )
    return data
  },

  async deleteMessage(messageId: number): Promise<MessagePublic> {
    const { data } = await apiClient.delete<MessagePublic>(
      `/chat/messages/${messageId}`,
    )
    return data
  },
}

// ============================================================================
// WebSocket events
// ============================================================================

export type ChatWsEventType =
  | 'message.new'
  | 'message.edit'
  | 'message.delete'
  | 'conversation.read'
  | 'typing'
  | 'presence'

export interface ChatWsEvent {
  type: ChatWsEventType
  conversation_id: number
  payload: Record<string, unknown>
}

export function buildChatWsUrl(token: string): string {
  // `/api/v1/chat/ws` — apiClient.baseURL emas, lekin nisbiy URL
  // Dev'da Vite proxy WebSocket ham proksilaydi (vite.config.ts)
  const base = import.meta.env.VITE_API_URL ?? '/api/v1'
  const isAbsolute = /^https?:\/\//i.test(base)
  if (isAbsolute) {
    const u = new URL(base)
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
    u.pathname = `${u.pathname.replace(/\/$/, '')}/chat/ws`
    u.searchParams.set('token', token)
    return u.toString()
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}${base.replace(/\/$/, '')}/chat/ws?token=${encodeURIComponent(token)}`
}
