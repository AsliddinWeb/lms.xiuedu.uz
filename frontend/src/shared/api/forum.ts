/**
 * Forum API klient — Phase 11b.
 *
 * Endpointlar `/api/v1/forum/*` ostida. Kurs-asosli (course-scoped) muhokama.
 */
import { apiClient } from './client'

export interface ForumThreadPublic {
  id: number
  course_id: number
  lesson_id: number | null
  author_id: number | null
  author_name: string | null
  title: string
  body: string | null
  is_pinned: boolean
  is_locked: boolean
  is_announcement: boolean
  view_count: number
  post_count: number
  last_reply_at: string | null
  created_at: string
  updated_at: string
}

export interface ForumPostPublic {
  id: number
  thread_id: number
  author_id: number | null
  author_name: string | null
  body: string
  parent_post_id: number | null
  like_count: number
  edited_at: string | null
  deleted_at: string | null
  created_at: string
  liked_by_me: boolean
}

export interface PaginatedThreads {
  items: ForumThreadPublic[]
  total: number
}

export interface PaginatedPosts {
  items: ForumPostPublic[]
  total: number
}

export const forumApi = {
  async listThreads(
    courseId: number,
    params: { page?: number; page_size?: number } = {},
  ): Promise<PaginatedThreads> {
    const { data } = await apiClient.get<PaginatedThreads>(
      `/forum/courses/${courseId}/threads`,
      { params },
    )
    return data
  },

  async getThread(threadId: number): Promise<ForumThreadPublic> {
    return (await apiClient.get<ForumThreadPublic>(`/forum/threads/${threadId}`)).data
  },

  async createThread(payload: {
    course_id: number
    lesson_id?: number | null
    title: string
    body?: string | null
    is_announcement?: boolean
  }): Promise<ForumThreadPublic> {
    return (
      await apiClient.post<ForumThreadPublic>('/forum/threads', payload)
    ).data
  },

  async updateThread(
    threadId: number,
    payload: {
      title?: string
      body?: string | null
      is_pinned?: boolean
      is_locked?: boolean
    },
  ): Promise<ForumThreadPublic> {
    return (
      await apiClient.patch<ForumThreadPublic>(`/forum/threads/${threadId}`, payload)
    ).data
  },

  async deleteThread(threadId: number): Promise<void> {
    await apiClient.delete(`/forum/threads/${threadId}`)
  },

  async listPosts(
    threadId: number,
    params: { page?: number; page_size?: number } = {},
  ): Promise<PaginatedPosts> {
    const { data } = await apiClient.get<PaginatedPosts>(
      `/forum/threads/${threadId}/posts`,
      { params },
    )
    return data
  },

  async createPost(
    threadId: number,
    payload: { body: string; parent_post_id?: number | null },
  ): Promise<ForumPostPublic> {
    return (
      await apiClient.post<ForumPostPublic>(
        `/forum/threads/${threadId}/posts`,
        payload,
      )
    ).data
  },

  async editPost(postId: number, body: string): Promise<ForumPostPublic> {
    return (
      await apiClient.patch<ForumPostPublic>(`/forum/posts/${postId}`, { body })
    ).data
  },

  async deletePost(postId: number): Promise<void> {
    await apiClient.delete(`/forum/posts/${postId}`)
  },

  async toggleLike(postId: number): Promise<ForumPostPublic> {
    return (await apiClient.post<ForumPostPublic>(`/forum/posts/${postId}/like`)).data
  },
}
