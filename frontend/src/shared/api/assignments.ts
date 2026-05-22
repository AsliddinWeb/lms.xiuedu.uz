import { apiClient } from './client'
import type {
  AnnotationItem,
  Appeal,
  AppealCreatePayload,
  AppealRespondPayload,
  AppealStatus,
  Assignment,
  AssignmentPayload,
  AssignmentType,
  GradePayload,
  PaginatedAppeals,
  PaginatedAssignments,
  PaginatedRubrics,
  PeerReview,
  PeerReviewSubmitPayload,
  PlagiarismCheckResult,
  Rubric,
  Submission,
  SubmissionCreatePayload,
  SubmissionStatus,
  SubmissionUploadResponse,
} from '@shared/types/assignments'

// ============================================================================
// Assignments
// ============================================================================

export const assignmentsApi = {
  async list(params: {
    course_id?: number
    lesson_id?: number
    is_published?: boolean
    only_active?: boolean
    enrolled_user_id?: number
    mine?: boolean
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedAssignments> {
    const { data } = await apiClient.get<PaginatedAssignments>('/assignments', { params })
    return data
  },

  async get(id: number): Promise<Assignment> {
    return (await apiClient.get<Assignment>(`/assignments/${id}`)).data
  },

  async create(payload: AssignmentPayload): Promise<Assignment> {
    return (await apiClient.post<Assignment>('/assignments', payload)).data
  },

  async update(id: number, payload: Partial<AssignmentPayload>): Promise<Assignment> {
    return (await apiClient.patch<Assignment>(`/assignments/${id}`, payload)).data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/assignments/${id}`)
  },

  async setPublished(id: number, isPublished: boolean): Promise<Assignment> {
    return (
      await apiClient.post<Assignment>(`/assignments/${id}/publish`, {
        is_published: isPublished,
      })
    ).data
  },

  async upload(id: number, file: File): Promise<SubmissionUploadResponse> {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await apiClient.post<SubmissionUploadResponse>(
      `/assignments/${id}/upload`,
      fd,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data
  },

  async submit(id: number, payload: SubmissionCreatePayload): Promise<Submission> {
    return (await apiClient.post<Submission>(`/assignments/${id}/submissions`, payload))
      .data
  },

  async listMySubmissions(assignmentId: number): Promise<Submission[]> {
    return (await apiClient.get<Submission[]>(`/assignments/${assignmentId}/my-submissions`))
      .data
  },

  async inbox(params: {
    course_id?: number
    assignment_id?: number
    status?: SubmissionStatus
    user_id?: number
    page?: number
    page_size?: number
  } = {}): Promise<{ items: Submission[]; total: number }> {
    const { data } = await apiClient.get('/submissions/inbox', { params })
    return data
  },
}

// ============================================================================
// Submissions (single)
// ============================================================================

export const submissionsApi = {
  async get(id: number): Promise<Submission> {
    return (await apiClient.get<Submission>(`/submissions/${id}`)).data
  },

  async grade(id: number, payload: GradePayload): Promise<Submission> {
    return (await apiClient.post<Submission>(`/submissions/${id}/grade`, payload)).data
  },

  async saveAnnotations(id: number, annotations: AnnotationItem[]): Promise<Submission> {
    return (
      await apiClient.put<Submission>(`/submissions/${id}/annotations`, {
        annotations,
      })
    ).data
  },

  async checkPlagiarism(id: number): Promise<PlagiarismCheckResult> {
    return (
      await apiClient.post<PlagiarismCheckResult>(`/submissions/${id}/check-plagiarism`)
    ).data
  },

  async createAppeal(id: number, payload: AppealCreatePayload): Promise<Appeal> {
    return (await apiClient.post<Appeal>(`/submissions/${id}/appeal`, payload)).data
  },
}

// ============================================================================
// Peer review (Phase 4e)
// ============================================================================

export const peerReviewsApi = {
  async listMine(onlyPending: boolean = true): Promise<PeerReview[]> {
    return (
      await apiClient.get<PeerReview[]>('/peer-reviews/my', {
        params: { only_pending: onlyPending },
      })
    ).data
  },

  async submit(id: number, payload: PeerReviewSubmitPayload): Promise<PeerReview> {
    return (await apiClient.post<PeerReview>(`/peer-reviews/${id}/submit`, payload)).data
  },
}

// ============================================================================
// Appeals (Phase 4e)
// ============================================================================

export const appealsApi = {
  async listMine(): Promise<Appeal[]> {
    return (await apiClient.get<Appeal[]>('/appeals/my')).data
  },

  async list(params: {
    status?: AppealStatus
    student_id?: number
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedAppeals> {
    const { data } = await apiClient.get<PaginatedAppeals>('/appeals', { params })
    return data
  },

  async respond(id: number, payload: AppealRespondPayload): Promise<Appeal> {
    return (await apiClient.post<Appeal>(`/appeals/${id}/respond`, payload)).data
  },
}

// ============================================================================
// Rubrics
// ============================================================================

export const rubricsApi = {
  async list(params: {
    organization_id?: number
    created_by?: number
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedRubrics> {
    const { data } = await apiClient.get<PaginatedRubrics>('/rubrics', { params })
    return data
  },

  async get(id: number): Promise<Rubric> {
    return (await apiClient.get<Rubric>(`/rubrics/${id}`)).data
  },

  async create(payload: {
    title: string
    description?: string | null
    organization_id?: number | null
    criteria: Array<{
      key: string
      name: string
      max_points: number | string
      levels?: Array<{ label: string; points: number | string; description?: string | null }>
    }>
  }): Promise<Rubric> {
    return (await apiClient.post<Rubric>('/rubrics', payload)).data
  },

  async update(id: number, payload: Partial<Rubric>): Promise<Rubric> {
    return (await apiClient.patch<Rubric>(`/rubrics/${id}`, payload)).data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/rubrics/${id}`)
  },
}

// Re-export type used in API for convenience
export type { AssignmentType }
