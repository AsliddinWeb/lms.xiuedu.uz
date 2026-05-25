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

export const gradebookApi = {
  async myGradebook(): Promise<GradebookRow[]> {
    const { data } = await apiClient.get<GradebookRow[]>('/me/gradebook')
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
