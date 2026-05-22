import { apiClient } from './client'

export type ProctoringSeverity = 'info' | 'warning' | 'critical'

export interface ProctoringEventPayload {
  event_type: string
  severity?: ProctoringSeverity
  metadata?: Record<string, unknown> | null
  occurred_at?: string | null
}

export interface ProctoringEventPublic {
  id: number
  attempt_id: number
  event_type: string
  severity: ProctoringSeverity
  event_metadata: Record<string, unknown> | null
  occurred_at: string
}

export interface ProctoringSnapshotPublic {
  id: number
  attempt_id: number
  object_key: string
  url: string
  face_count: number | null
  face_match_score: string | null  // Decimal string from backend (0..1)
  width: number | null
  height: number | null
  bytes_size: number | null
  captured_at: string
}

export interface ViolationScore {
  attempt_id: number
  violation_score: number
  flagged: boolean
}

export interface IdReferencePhoto {
  id: number
  attempt_id: number
  url: string
  captured_at: string
}

export const proctoringApi = {
  async event(attemptId: number, payload: ProctoringEventPayload): Promise<ProctoringEventPublic> {
    return (
      await apiClient.post<ProctoringEventPublic>(
        `/attempts/${attemptId}/proctoring/event`,
        payload,
      )
    ).data
  },

  async listEvents(attemptId: number): Promise<ProctoringEventPublic[]> {
    return (
      await apiClient.get<ProctoringEventPublic[]>(`/attempts/${attemptId}/proctoring/events`)
    ).data
  },

  async snapshot(
    attemptId: number,
    blob: Blob,
    opts: {
      face_count?: number | null
      face_match_score?: number | null
      width?: number
      height?: number
    } = {},
  ): Promise<ProctoringSnapshotPublic> {
    const form = new FormData()
    form.append('image', blob, `snap_${Date.now()}.jpg`)
    if (opts.face_count !== undefined && opts.face_count !== null)
      form.append('face_count', String(opts.face_count))
    if (opts.face_match_score !== undefined && opts.face_match_score !== null)
      form.append('face_match_score', String(opts.face_match_score))
    if (opts.width !== undefined) form.append('width', String(opts.width))
    if (opts.height !== undefined) form.append('height', String(opts.height))
    return (
      await apiClient.post<ProctoringSnapshotPublic>(
        `/attempts/${attemptId}/proctoring/snapshot`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
    ).data
  },

  async listSnapshots(attemptId: number): Promise<ProctoringSnapshotPublic[]> {
    return (
      await apiClient.get<ProctoringSnapshotPublic[]>(
        `/attempts/${attemptId}/proctoring/snapshots`,
      )
    ).data
  },

  async getIdReference(attemptId: number): Promise<IdReferencePhoto | null> {
    const { data } = await apiClient.get<IdReferencePhoto | null>(
      `/attempts/${attemptId}/proctoring/id-reference`,
    )
    return data
  },

  async uploadIdReference(attemptId: number, blob: Blob): Promise<IdReferencePhoto> {
    const form = new FormData()
    form.append('image', blob, `id_ref_${Date.now()}.jpg`)
    return (
      await apiClient.post<IdReferencePhoto>(
        `/attempts/${attemptId}/proctoring/id-reference`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
    ).data
  },

  async score(attemptId: number): Promise<ViolationScore> {
    return (
      await apiClient.get<ViolationScore>(`/attempts/${attemptId}/proctoring/score`)
    ).data
  },
}
