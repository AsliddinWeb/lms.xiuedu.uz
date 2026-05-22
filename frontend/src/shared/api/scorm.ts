/**
 * SCORM API client — Phase 11a.
 */
import { apiClient } from '@shared/api/client'

export interface ScormPackage {
  id: number
  content_item_id: number
  version: string
  manifest_identifier: string | null
  title: string | null
  description: string | null
  launch_url: string
  package_path: string
  file_size: number | null
  mastery_score: string | null
  uploaded_at: string
  launch_full_url: string | null
}

export interface ScormAttempt {
  id: number
  user_id: number
  package_id: number
  lesson_id: number | null
  attempt_number: number
  status: string
  cmi_data: Record<string, unknown>
  score_raw: string | null
  score_min: string | null
  score_max: string | null
  total_time: string | null
  session_time: string | null
  bookmark: string | null
  suspend_data: string | null
  started_at: string
  completed_at: string | null
  last_accessed_at: string
}

export interface StartAttemptResponse {
  attempt: ScormAttempt
  package: ScormPackage
  launch_full_url: string
}

export const scormApi = {
  async upload(file: File, contentItemId: number): Promise<ScormPackage> {
    const form = new FormData()
    form.append('file', file)
    form.append('content_item_id', String(contentItemId))
    const { data } = await apiClient.post<ScormPackage>(
      '/scorm/packages/upload',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data
  },

  async getPackage(packageId: number): Promise<ScormPackage> {
    return (await apiClient.get<ScormPackage>(`/scorm/packages/${packageId}`)).data
  },

  async start(packageId: number, lessonId?: number): Promise<StartAttemptResponse> {
    const params = lessonId ? { lesson_id: lessonId } : {}
    return (
      await apiClient.post<StartAttemptResponse>(
        `/scorm/packages/${packageId}/start`,
        null,
        { params },
      )
    ).data
  },

  async getAttempt(attemptId: number): Promise<ScormAttempt> {
    return (await apiClient.get<ScormAttempt>(`/scorm/attempts/${attemptId}`)).data
  },

  async commit(
    attemptId: number,
    cmiUpdates: Record<string, unknown>,
  ): Promise<ScormAttempt> {
    return (
      await apiClient.post<ScormAttempt>(`/scorm/attempts/${attemptId}/commit`, {
        cmi_updates: cmiUpdates,
      })
    ).data
  },

  async finish(attemptId: number): Promise<ScormAttempt> {
    return (await apiClient.post<ScormAttempt>(`/scorm/attempts/${attemptId}/finish`)).data
  },
}
