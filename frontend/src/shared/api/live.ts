import { apiClient } from './client'
import type {
  AttendanceSummary,
  CalendarTokenResponse,
  LiveAdmissionItem,
  LiveAttendance,
  LiveAttendanceItem,
  LiveJoinInfo,
  LiveSession,
  LiveSessionCreatePayload,
  LiveSessionUpdatePayload,
  PaginatedLiveSessions,
} from '@shared/types/live'

export const liveSessionsApi = {
  async list(params: {
    status?: string
    course_id?: number
    lesson_id?: number
    host_user_id?: number
    starts_after?: string
    starts_before?: string
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedLiveSessions> {
    const { data } = await apiClient.get<PaginatedLiveSessions>('/live-sessions', {
      params,
    })
    return data
  },

  async get(id: number): Promise<LiveSession> {
    return (await apiClient.get<LiveSession>(`/live-sessions/${id}`)).data
  },

  async create(payload: LiveSessionCreatePayload): Promise<LiveSession> {
    return (await apiClient.post<LiveSession>('/live-sessions', payload)).data
  },

  async update(
    id: number,
    payload: LiveSessionUpdatePayload,
  ): Promise<LiveSession> {
    return (await apiClient.patch<LiveSession>(`/live-sessions/${id}`, payload))
      .data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/live-sessions/${id}`)
  },

  async start(id: number): Promise<LiveSession> {
    return (await apiClient.post<LiveSession>(`/live-sessions/${id}/start`)).data
  },

  async end(id: number): Promise<LiveSession> {
    return (await apiClient.post<LiveSession>(`/live-sessions/${id}/end`)).data
  },

  async cancel(id: number): Promise<LiveSession> {
    return (await apiClient.post<LiveSession>(`/live-sessions/${id}/cancel`))
      .data
  },

  async getJoinInfo(id: number): Promise<LiveJoinInfo> {
    return (await apiClient.get<LiveJoinInfo>(`/live-sessions/${id}/join-info`))
      .data
  },

  async join(id: number): Promise<LiveAttendance> {
    return (await apiClient.post<LiveAttendance>(`/live-sessions/${id}/join`))
      .data
  },

  async leave(id: number): Promise<LiveAttendance> {
    return (await apiClient.post<LiveAttendance>(`/live-sessions/${id}/leave`))
      .data
  },

  async listAttendance(id: number): Promise<LiveAttendanceItem[]> {
    return (
      await apiClient.get<LiveAttendanceItem[]>(`/live-sessions/${id}/attendance`)
    ).data
  },

  // Waiting room — kutayotgan kirish so'rovlari (host)
  async listAdmissions(id: number): Promise<LiveAdmissionItem[]> {
    return (
      await apiClient.get<LiveAdmissionItem[]>(`/live-sessions/${id}/admissions`)
    ).data
  },

  async decideAdmission(
    id: number,
    userId: number,
    approve: boolean,
  ): Promise<void> {
    await apiClient.post(`/live-sessions/${id}/admissions/${userId}`, { approve })
  },

  async uploadRecording(
    id: number,
    file: File,
    onProgress?: (loaded: number, total: number) => void,
  ): Promise<LiveSession> {
    const form = new FormData()
    form.append('file', file)
    const { data } = await apiClient.post<LiveSession>(
      `/live-sessions/${id}/recording-upload`,
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(e.loaded, e.total)
        },
      },
    )
    return data
  },

  async deleteRecording(id: number): Promise<LiveSession> {
    return (await apiClient.delete<LiveSession>(`/live-sessions/${id}/recording`))
      .data
  },

  async getAttendanceSummary(id: number): Promise<AttendanceSummary> {
    return (
      await apiClient.get<AttendanceSummary>(
        `/live-sessions/${id}/attendance/summary`,
      )
    ).data
  },

  async recomputeAttendance(id: number): Promise<AttendanceSummary> {
    return (
      await apiClient.post<AttendanceSummary>(
        `/live-sessions/${id}/attendance/recompute`,
      )
    ).data
  },

  async getCalendarToken(): Promise<CalendarTokenResponse> {
    return (
      await apiClient.get<CalendarTokenResponse>('/live-calendar/token')
    ).data
  },
}

// ============================================================================
// Phase 7a — LiveRecording (browser MediaRecorder upload)
// ============================================================================

export interface LiveRecording {
  id: number
  session_id: number
  recorded_by: number | null
  status: 'recording' | 'finalized' | 'failed'
  object_key: string | null
  url: string | null
  mime_type: string
  started_at: string
  finalized_at: string | null
  duration_seconds: number | null
  file_size_bytes: number | null
  created_at: string
  updated_at: string
}

export const liveRecordingsApi = {
  async start(sessionId: number): Promise<LiveRecording> {
    return (
      await apiClient.post<LiveRecording>(
        `/live-sessions/${sessionId}/recordings/start`,
      )
    ).data
  },

  async upload(
    recordingId: number,
    blob: Blob,
    durationSeconds: number | null = null,
  ): Promise<LiveRecording> {
    const form = new FormData()
    form.append('blob', blob, `rec_${recordingId}.webm`)
    const params: Record<string, number> = {}
    if (durationSeconds !== null) params.duration_seconds = durationSeconds
    return (
      await apiClient.post<LiveRecording>(
        `/live-recordings/${recordingId}/upload`,
        form,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          params,
          // Katta yozuv ham cheksiz osilib qolmasin (30 daqiqa ceiling)
          timeout: 30 * 60 * 1000,
        },
      )
    ).data
  },

  async list(sessionId: number): Promise<LiveRecording[]> {
    return (
      await apiClient.get<LiveRecording[]>(
        `/live-sessions/${sessionId}/recordings`,
      )
    ).data
  },

  async remove(recordingId: number): Promise<void> {
    await apiClient.delete(`/live-recordings/${recordingId}`)
  },
}

// ============================================================================
// Phase 9c — Captions
// ============================================================================

export interface LiveCaptionItem {
  start_ms: number
  end_ms: number
  text: string
  lang: string
}

export interface LiveCaptionPublic extends LiveCaptionItem {
  id: number
  session_id: number
  speaker_user_id: number | null
}

export const liveCaptionsApi = {
  async postBatch(sessionId: number, items: LiveCaptionItem[]): Promise<number> {
    const { data } = await apiClient.post<{ inserted: number }>(
      `/live-sessions/${sessionId}/captions/batch`,
      { items },
    )
    return data.inserted
  },

  async list(sessionId: number): Promise<LiveCaptionPublic[]> {
    const { data } = await apiClient.get<LiveCaptionPublic[]>(
      `/live-sessions/${sessionId}/captions`,
    )
    return data
  },

  vttUrl(sessionId: number): string {
    return `/api/v1/live-sessions/${sessionId}/captions.vtt`
  },
}
