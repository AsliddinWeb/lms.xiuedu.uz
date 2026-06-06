// Live darslar (Phase 5a + 5b) — backend Pydantic schemalar bilan teng.

export type LiveProvider = 'native'
export type LiveStatus = 'scheduled' | 'live' | 'ended' | 'cancelled'

export interface LiveSession {
  id: number
  organization_id: number | null
  course_id: number | null
  lesson_id: number | null

  title: string
  description: string | null

  scheduled_start: string
  scheduled_end: string
  duration_minutes: number

  provider: LiveProvider
  provider_meeting_id: string | null
  provider_metadata: Record<string, unknown>

  host_user_id: number
  host_full_name?: string | null
  status: LiveStatus
  actual_start: string | null
  actual_end: string | null

  is_recording_enabled: boolean
  recording_url: string | null
  thumbnail_url: string | null
  recording_size_bytes: number | null
  recording_duration_seconds: number | null
  recording_mime_type: string | null
  min_attendance_percent: number
  requires_approval?: boolean

  created_at: string
  updated_at: string
}

export interface LiveSessionCreatePayload {
  title: string
  description?: string | null
  course_id?: number | null
  lesson_id?: number | null
  scheduled_start: string
  scheduled_end: string
  duration_minutes: number
  provider?: LiveProvider
  is_recording_enabled?: boolean
  min_attendance_percent?: number
  requires_approval?: boolean
}

export type LiveSessionUpdatePayload = Partial<LiveSessionCreatePayload>

export interface LiveAdmissionItem {
  user_id: number
  full_name: string
  email: string | null
  status: string
  requested_at: string
}

export interface PaginatedLiveSessions {
  items: LiveSession[]
  total: number
}

export interface LiveAttendance {
  id: number
  session_id: number
  user_id: number
  joined_at: string | null
  left_at: string | null
  total_minutes: number
  is_counted: boolean
}

export interface LiveAttendanceItem {
  user_id: number
  full_name: string
  email: string
  joined_at: string | null
  left_at: string | null
  total_minutes: number
  is_counted: boolean
}

export interface AttendanceSummary {
  session_id: number
  status: LiveStatus
  duration_minutes: number
  min_attendance_percent: number
  total_participants: number
  joined_participants: number
  counted_participants: number
  counted_percent: number
  average_minutes: number
}

export interface CalendarTokenResponse {
  url: string
  token: string
}

export interface LiveJoinInfo {
  session_id: number
  provider: LiveProvider
  room_name: string
  join_url: string
  is_host: boolean
  embed_token: string | null
  embed_config: Record<string, unknown> | null
  pending?: boolean
}
