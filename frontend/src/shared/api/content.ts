import { apiClient } from './client'
import type {
  ContentCreatePayload,
  ContentItem,
  ContentStatus,
  ContentType,
  PaginatedContent,
} from '@shared/types/content'

export const contentApi = {
  async list(params: {
    type?: ContentType
    status?: ContentStatus
    subject_id?: number
    author_id?: number
    language?: string
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedContent> {
    const { data } = await apiClient.get<PaginatedContent>('/content', { params })
    return data
  },
  async get(id: number): Promise<ContentItem> {
    return (await apiClient.get<ContentItem>(`/content/${id}`)).data
  },
  async create(payload: ContentCreatePayload): Promise<ContentItem> {
    return (await apiClient.post<ContentItem>('/content', payload)).data
  },
  async transition(id: number, status: ContentStatus): Promise<ContentItem> {
    return (await apiClient.post<ContentItem>(`/content/${id}/publish`, { status })).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/content/${id}`)
  },
}
