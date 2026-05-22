import { apiClient } from './client'

export interface ExamReportItem {
  exam_id: number
  exam_title: string
  exam_type: string
  exam_status: string
  course_id: number
  course_title: string
  attempts: number
  avg_percentage: number
  passed_count: number
  flagged_count: number
  pass_rate: number
}

export interface ExamReportSummary {
  total_exams: number
  total_attempts: number
  avg_percentage: number
  pass_rate: number
  items: ExamReportItem[]
}

export interface ExamReportFilters {
  course_id?: number | null
  type?: string | null
  date_from?: string | null
  date_to?: string | null
}

function cleanParams(p: ExamReportFilters): Record<string, string | number> {
  const out: Record<string, string | number> = {}
  for (const [k, v] of Object.entries(p)) {
    if (v !== null && v !== undefined && v !== '') out[k] = v as string | number
  }
  return out
}

export const reportsApi = {
  async examSummary(filters: ExamReportFilters = {}): Promise<ExamReportSummary> {
    const { data } = await apiClient.get<ExamReportSummary>('/reports/exams/summary', {
      params: cleanParams(filters),
    })
    return data
  },

  /** Returns a path that downloads the CSV when the user clicks it. */
  csvDownloadUrl(filters: ExamReportFilters = {}): string {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(cleanParams(filters))) {
      params.set(k, String(v))
    }
    const qs = params.toString()
    return `/api/v1/reports/exams/csv${qs ? `?${qs}` : ''}`
  },

  async downloadCsv(filters: ExamReportFilters = {}): Promise<Blob> {
    const { data } = await apiClient.get<Blob>('/reports/exams/csv', {
      params: cleanParams(filters),
      responseType: 'blob',
    })
    return data
  },
}
