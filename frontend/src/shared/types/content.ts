// Content types — backend Pydantic schemalar bilan teng.

export type ContentType = 'text' | 'video' | 'pdf' | 'file' | 'link'
export type ContentStatus = 'draft' | 'review' | 'published' | 'archived'
export type ContentLanguage = 'uz-lat' | 'uz-cyr' | 'ru' | 'en'

export interface ContentItem {
  id: number
  type: ContentType
  title: string
  description: string | null
  subject_id: number | null
  author_id: number
  file_url: string | null
  mime_type: string | null
  file_size: number | null
  duration_seconds: number | null
  content_data: Record<string, unknown>
  language: ContentLanguage
  tags: string[]
  version: number
  parent_id: number | null
  status: ContentStatus
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedContent {
  items: ContentItem[]
  total: number
}

export interface ContentCreatePayload {
  type: ContentType
  title: string
  description?: string | null
  subject_id?: number | null
  file_url?: string | null
  mime_type?: string | null
  file_size?: number | null
  duration_seconds?: number | null
  content_data?: Record<string, unknown>
  language?: ContentLanguage
  tags?: string[]
}
