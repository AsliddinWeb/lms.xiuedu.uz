/**
 * Lesson comments API klient — Phase 11c.
 *
 * Endpointlar /api/v1/lessons/{lesson_id}/comments ostida.
 */
import { apiClient } from './client'

export interface LessonCommentPublic {
  id: number
  lesson_id: number
  author_id: number | null
  author_name: string | null
  body: string
  parent_comment_id: number | null
  like_count: number
  edited_at: string | null
  deleted_at: string | null
  created_at: string
  liked_by_me: boolean
}

export interface PaginatedComments {
  items: LessonCommentPublic[]
  total: number
}

export const commentsApi = {
  async list(
    lessonId: number,
    params: { page?: number; page_size?: number } = {},
  ): Promise<PaginatedComments> {
    const { data } = await apiClient.get<PaginatedComments>(
      `/lessons/${lessonId}/comments`,
      { params },
    )
    return data
  },

  async create(
    lessonId: number,
    payload: { body: string; parent_comment_id?: number | null },
  ): Promise<LessonCommentPublic> {
    return (
      await apiClient.post<LessonCommentPublic>(
        `/lessons/${lessonId}/comments`,
        payload,
      )
    ).data
  },

  async edit(commentId: number, body: string): Promise<LessonCommentPublic> {
    return (
      await apiClient.patch<LessonCommentPublic>(
        `/lessons/comments/${commentId}`,
        { body },
      )
    ).data
  },

  async remove(commentId: number): Promise<void> {
    await apiClient.delete(`/lessons/comments/${commentId}`)
  },

  async toggleLike(commentId: number): Promise<LessonCommentPublic> {
    return (
      await apiClient.post<LessonCommentPublic>(
        `/lessons/comments/${commentId}/like`,
      )
    ).data
  },
}
