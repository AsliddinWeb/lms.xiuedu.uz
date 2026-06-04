import { apiClient } from './client'
import type {
  Course,
  CoursePayload,
  CourseProgress,
  CourseStatus,
  CourseType,
  Enrollment,
  EnrollmentMethod,
  Lesson,
  LessonPayload,
  LessonProgress,
  Module,
  ModulePayload,
  PaginatedCourses,
  PaginatedStudents,
} from '@shared/types/courses'

// ============================================================================
// Course
// ============================================================================
export const coursesApi = {
  async list(params: {
    type?: CourseType
    status?: CourseStatus
    subject_id?: number
    organization_id?: number
    language?: string
    primary_author_id?: number
    enrolled_user_id?: number
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedCourses> {
    const { data } = await apiClient.get<PaginatedCourses>('/courses', { params })
    return data
  },
  async get(id: number): Promise<Course> {
    return (await apiClient.get<Course>(`/courses/${id}`)).data
  },
  async create(payload: CoursePayload): Promise<Course> {
    return (await apiClient.post<Course>('/courses', payload)).data
  },
  async update(id: number, payload: Partial<CoursePayload>): Promise<Course> {
    return (await apiClient.patch<Course>(`/courses/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/courses/${id}`)
  },
  async publish(id: number): Promise<Course> {
    return (await apiClient.post<Course>(`/courses/${id}/publish`)).data
  },
  async unpublish(id: number): Promise<Course> {
    return (await apiClient.post<Course>(`/courses/${id}/unpublish`)).data
  },
}

// ============================================================================
// Module
// ============================================================================
export const modulesApi = {
  async list(courseId: number): Promise<Module[]> {
    return (await apiClient.get<Module[]>(`/courses/${courseId}/modules`)).data
  },
  async create(courseId: number, payload: ModulePayload): Promise<Module> {
    return (await apiClient.post<Module>(`/courses/${courseId}/modules`, payload)).data
  },
  async update(id: number, payload: Partial<ModulePayload>): Promise<Module> {
    return (await apiClient.patch<Module>(`/modules/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/modules/${id}`)
  },
  async reorder(courseId: number, orderedIds: number[]): Promise<Module[]> {
    return (
      await apiClient.post<Module[]>(`/courses/${courseId}/modules/reorder`, {
        ordered_ids: orderedIds,
      })
    ).data
  },
}

// ============================================================================
// Lesson
// ============================================================================
export const lessonsApi = {
  async list(moduleId: number): Promise<Lesson[]> {
    return (await apiClient.get<Lesson[]>(`/modules/${moduleId}/lessons`)).data
  },
  async create(moduleId: number, payload: LessonPayload): Promise<Lesson> {
    return (await apiClient.post<Lesson>(`/modules/${moduleId}/lessons`, payload)).data
  },
  async update(id: number, payload: Partial<LessonPayload>): Promise<Lesson> {
    return (await apiClient.patch<Lesson>(`/lessons/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/lessons/${id}`)
  },
  async reorder(moduleId: number, orderedIds: number[]): Promise<Lesson[]> {
    return (
      await apiClient.post<Lesson[]>(`/modules/${moduleId}/lessons/reorder`, {
        ordered_ids: orderedIds,
      })
    ).data
  },
}

// ============================================================================
// Enrollment + Progress
// ============================================================================
export const enrollmentsApi = {
  async selfEnroll(courseId: number): Promise<Enrollment> {
    return (await apiClient.post<Enrollment>(`/courses/${courseId}/enroll`)).data
  },
  async selfUnenroll(courseId: number): Promise<void> {
    await apiClient.delete(`/courses/${courseId}/enroll`)
  },
  async listStudents(
    courseId: number,
    params: { page?: number; page_size?: number } = {},
  ): Promise<PaginatedStudents> {
    return (
      await apiClient.get<PaginatedStudents>(`/courses/${courseId}/students`, {
        params,
      })
    ).data
  },
  async addStudent(
    courseId: number,
    userId: number,
    method: EnrollmentMethod = 'manual',
  ): Promise<Enrollment> {
    return (
      await apiClient.post<Enrollment>(`/courses/${courseId}/students`, {
        user_id: userId,
        enrollment_method: method,
      })
    ).data
  },
  async removeStudent(courseId: number, userId: number): Promise<void> {
    await apiClient.delete(`/courses/${courseId}/students/${userId}`)
  },
}

export const progressApi = {
  async myCourseProgress(courseId: number): Promise<CourseProgress> {
    return (await apiClient.get<CourseProgress>(`/courses/${courseId}/my-progress`)).data
  },
  async start(lessonId: number): Promise<LessonProgress> {
    return (await apiClient.post<LessonProgress>(`/lessons/${lessonId}/start`)).data
  },
  async complete(lessonId: number): Promise<LessonProgress> {
    return (await apiClient.post<LessonProgress>(`/lessons/${lessonId}/complete`)).data
  },
}

// Phase 13.20 — Gradebook
export interface GradebookRow {
  course_id: number
  title: string
  teacher: string
  credits: number
  current_avg: string
  midterm: string
  final: string
  total: string
  grade_letter: string
  grade_number: number
  grade_variant: 'success' | 'warning' | 'danger'
}

// Phase 18.2 — kurs pedagog'i public profili
export interface CourseTeacher {
  id: number
  full_name: string
  avatar_url: string | null
  bio: string | null
  courses_count: number
}

export const courseTeacherApi = {
  async get(courseId: number): Promise<CourseTeacher> {
    const { data } = await apiClient.get<CourseTeacher>(
      `/courses/${courseId}/teacher`,
    )
    return data
  },
}

// Phase 18.3 — kurs materiallari (lesson content_items)
export interface CourseMaterial {
  lesson_id: number
  lesson_title: string
  module_id: number
  content_id: number | null
  title: string | null
  type: string | null
  file_url: string | null
  mime_type: string | null
  file_size: number | null
}

export const courseMaterialsApi = {
  async list(courseId: number): Promise<CourseMaterial[]> {
    const { data } = await apiClient.get<CourseMaterial[]>(
      `/courses/${courseId}/materials`,
    )
    return data
  },
}

export const gradebookApi = {
  async myGradebook(): Promise<GradebookRow[]> {
    const { data } = await apiClient.get<GradebookRow[]>('/me/gradebook')
    return data
  },
  async downloadCsv(): Promise<Blob> {
    const { data } = await apiClient.get<Blob>('/me/gradebook.csv', {
      responseType: 'blob',
    })
    return data
  },
}

// Phase 18.5 — Kurs detail right column: yaqin imtihonlar + live darslar
export interface UpcomingExamItem {
  id: number
  title: string
  type: string
  duration_minutes: number
  available_from: string | null
  available_until: string | null
  proctoring_enabled: boolean
}

export interface UpcomingLiveItem {
  id: number
  title: string
  scheduled_start: string
  scheduled_end: string
  duration_minutes: number
  status: string
  host_user_id: number
  host_full_name: string | null
}

export const courseUpcomingApi = {
  async exams(courseId: number, limit = 5): Promise<UpcomingExamItem[]> {
    const { data } = await apiClient.get<UpcomingExamItem[]>(
      `/courses/${courseId}/upcoming-exams`,
      { params: { limit } },
    )
    return data
  },
  async live(courseId: number, limit = 5): Promise<UpcomingLiveItem[]> {
    const { data } = await apiClient.get<UpcomingLiveItem[]>(
      `/courses/${courseId}/upcoming-live`,
      { params: { limit } },
    )
    return data
  },
}

// Phase 16 — Talaba activity agregati (dashboard chart)
export interface ActivityDay {
  date: string
  completed_count: number
  time_minutes: number
}

export interface ActivityResponse {
  days: ActivityDay[]
  total_minutes: number
  total_completed: number
  streak_days: number
  most_active_label: string | null
}

export const activityApi = {
  async my(days: 7 | 30 | 365 = 7): Promise<ActivityResponse> {
    const { data } = await apiClient.get<ActivityResponse>('/me/activity', {
      params: { days },
    })
    return data
  },
}

// Phase 19 — Course Reviews (talaba sharhlari va reytingi)
export interface CourseReviewItem {
  id: number
  user_id: number
  user_full_name: string
  user_avatar_url: string | null
  rating: number
  comment: string | null
  created_at: string
  updated_at: string
}

export interface CourseReviewAggregate {
  avg_rating: number
  total: number
  distribution: Record<string, number>
}

export interface CourseReviewListResponse {
  items: CourseReviewItem[]
  aggregate: CourseReviewAggregate
  my_review: CourseReviewItem | null
}

export interface CourseReviewPayload {
  rating: number
  comment?: string | null
}

export const courseReviewsApi = {
  async list(courseId: number): Promise<CourseReviewListResponse> {
    const { data } = await apiClient.get<CourseReviewListResponse>(
      `/courses/${courseId}/reviews`,
    )
    return data
  },
  async create(
    courseId: number,
    payload: CourseReviewPayload,
  ): Promise<CourseReviewItem> {
    const { data } = await apiClient.post<CourseReviewItem>(
      `/courses/${courseId}/reviews`,
      payload,
    )
    return data
  },
  async updateMine(
    courseId: number,
    payload: CourseReviewPayload,
  ): Promise<CourseReviewItem> {
    const { data } = await apiClient.patch<CourseReviewItem>(
      `/courses/${courseId}/reviews/me`,
      payload,
    )
    return data
  },
  async deleteMine(courseId: number): Promise<void> {
    await apiClient.delete(`/courses/${courseId}/reviews/me`)
  },
}
