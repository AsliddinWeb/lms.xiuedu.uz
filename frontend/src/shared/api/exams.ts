import { apiClient } from './client'
import type {
  AnswerFileUpload,
  AnswerPublic,
  AnswerSubmit,
  AttemptPublic,
  AttemptResult,
  AttemptStudentSummary,
  AttemptTakeView,
  CodeRunResponse,
  CodeTestCase,
  CodeTestCasePayload,
  Exam,
  ExamPayload,
  ExamStatus,
  ExamType,
  ExamUpdatePayload,
  GradeAttemptPayload,
  PaginatedAttempts,
  PaginatedExams,
  QuestionPayload,
  QuestionPublic,
} from '@shared/types/exams'

// ============================================================================
// Exams
// ============================================================================

export const examsApi = {
  async list(params: {
    course_id?: number
    lesson_id?: number
    type?: ExamType
    status?: ExamStatus
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedExams> {
    const { data } = await apiClient.get<PaginatedExams>('/exams', { params })
    return data
  },

  /** Talaba uchun: yozilgan kurslardagi published imtihonlar. */
  async my(params: { course_id?: number; page?: number; page_size?: number } = {}): Promise<PaginatedExams> {
    const { data } = await apiClient.get<PaginatedExams>('/exams/my', { params })
    return data
  },

  async get(id: number): Promise<Exam> {
    return (await apiClient.get<Exam>(`/exams/${id}`)).data
  },

  async create(payload: ExamPayload): Promise<Exam> {
    return (await apiClient.post<Exam>('/exams', payload)).data
  },

  async update(id: number, payload: ExamUpdatePayload): Promise<Exam> {
    return (await apiClient.patch<Exam>(`/exams/${id}`, payload)).data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/exams/${id}`)
  },

  async publish(id: number): Promise<Exam> {
    return (await apiClient.post<Exam>(`/exams/${id}/publish`)).data
  },

  async archive(id: number): Promise<Exam> {
    return (await apiClient.post<Exam>(`/exams/${id}/archive`)).data
  },
}

// ============================================================================
// Questions
// ============================================================================

export const questionsApi = {
  async list(examId: number): Promise<QuestionPublic[]> {
    return (await apiClient.get<QuestionPublic[]>(`/exams/${examId}/questions`)).data
  },

  async create(examId: number, payload: QuestionPayload): Promise<QuestionPublic> {
    return (
      await apiClient.post<QuestionPublic>(`/exams/${examId}/questions`, payload)
    ).data
  },

  async update(id: number, payload: Partial<QuestionPayload>): Promise<QuestionPublic> {
    return (await apiClient.patch<QuestionPublic>(`/questions/${id}`, payload)).data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/questions/${id}`)
  },

  async reorder(examId: number, ids: number[]): Promise<QuestionPublic[]> {
    return (
      await apiClient.post<QuestionPublic[]>(`/exams/${examId}/questions/reorder`, { ids })
    ).data
  },
}

// ============================================================================
// Attempts
// ============================================================================

export const attemptsApi = {
  async start(examId: number): Promise<AttemptTakeView> {
    return (await apiClient.post<AttemptTakeView>(`/exams/${examId}/start`)).data
  },

  async myAttempts(examId: number): Promise<AttemptStudentSummary[]> {
    return (
      await apiClient.get<AttemptStudentSummary[]>(`/exams/${examId}/my-attempts`)
    ).data
  },

  async get(id: number): Promise<AttemptTakeView> {
    return (await apiClient.get<AttemptTakeView>(`/attempts/${id}`)).data
  },

  async saveAnswer(id: number, payload: AnswerSubmit): Promise<AnswerPublic> {
    return (await apiClient.post<AnswerPublic>(`/attempts/${id}/answer`, payload)).data
  },

  async uploadFile(
    attemptId: number,
    questionId: number,
    file: File,
  ): Promise<AnswerFileUpload> {
    const fd = new FormData()
    fd.append('question_id', String(questionId))
    fd.append('file', file)
    const { data } = await apiClient.post<AnswerFileUpload>(
      `/attempts/${attemptId}/upload`,
      fd,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data
  },

  async submit(id: number): Promise<AttemptResult> {
    return (await apiClient.post<AttemptResult>(`/attempts/${id}/submit`)).data
  },

  async result(id: number): Promise<AttemptResult> {
    return (await apiClient.get<AttemptResult>(`/attempts/${id}/result`)).data
  },

  async listForExam(
    examId: number,
    params: {
      user_id?: number
      status?: string
      page?: number
      page_size?: number
    } = {},
  ): Promise<PaginatedAttempts> {
    return (
      await apiClient.get<PaginatedAttempts>(`/exams/${examId}/attempts`, { params })
    ).data
  },

  async grade(id: number, payload: GradeAttemptPayload): Promise<AttemptPublic> {
    return (await apiClient.post<AttemptPublic>(`/attempts/${id}/grade`, payload)).data
  },

  async invalidate(id: number, reason: string): Promise<AttemptPublic> {
    return (
      await apiClient.post<AttemptPublic>(`/attempts/${id}/invalidate`, { reason })
    ).data
  },

  // Phase 8f — CSV export. Blob orqali yuklaydi (cookie auth saqlanadi).
  async exportAttemptsCsv(
    examId: number,
    params: { user_id?: number; status?: string } = {},
  ): Promise<Blob> {
    const res = await apiClient.get<Blob>(`/exams/${examId}/attempts.csv`, {
      params,
      responseType: 'blob',
    })
    return res.data
  },
}

// ============================================================================
// Phase 9d — Code test cases + run
// ============================================================================

export const codeTestCasesApi = {
  async list(questionId: number): Promise<CodeTestCase[]> {
    return (await apiClient.get<CodeTestCase[]>(`/questions/${questionId}/test-cases`)).data
  },

  async create(questionId: number, payload: CodeTestCasePayload): Promise<CodeTestCase> {
    return (
      await apiClient.post<CodeTestCase>(`/questions/${questionId}/test-cases`, payload)
    ).data
  },

  async update(id: number, payload: Partial<CodeTestCasePayload>): Promise<CodeTestCase> {
    return (await apiClient.patch<CodeTestCase>(`/code-test-cases/${id}`, payload)).data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/code-test-cases/${id}`)
  },

  async runForAttempt(
    attemptId: number,
    questionId: number,
    code: string,
  ): Promise<CodeRunResponse> {
    return (
      await apiClient.post<CodeRunResponse>(
        `/attempts/${attemptId}/questions/${questionId}/run-code`,
        { code },
      )
    ).data
  },
}
