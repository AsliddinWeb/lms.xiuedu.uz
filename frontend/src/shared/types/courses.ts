// Courses types — backend Pydantic schemalar bilan teng.

export type CourseType = 'academic' | 'open' | 'micro' | 'specialization'
export type CourseLevel = 'beginner' | 'intermediate' | 'advanced'
export type CourseStatus = 'draft' | 'published' | 'archived'
export type EnrollmentType = 'auto' | 'manual' | 'self'
export type EnrollmentMethod = 'auto' | 'manual' | 'self'
export type CompletionStatus = 'in_progress' | 'completed' | 'failed' | 'dropped'
export type LangCode = 'uz-lat' | 'uz-cyr' | 'ru' | 'en'

export interface Course {
  id: number
  code: string | null
  title: string
  slug: string
  description: string | null
  subject_id: number | null
  organization_id: number | null
  type: CourseType
  level: CourseLevel | null
  language: LangCode
  cover_image_url: string | null
  trailer_video_url: string | null
  duration_weeks: number | null
  estimated_hours: number | null
  objectives: string[]
  skills_gained: string[]
  status: CourseStatus
  published_at: string | null
  enrollment_type: EnrollmentType
  max_students: number | null
  primary_author_id: number | null
  enrollment_count?: number | null
  created_at: string
  updated_at: string
}

export interface PaginatedCourses {
  items: Course[]
  total: number
}

export interface CoursePayload {
  code?: string | null
  title: string
  slug: string
  description?: string | null
  subject_id?: number | null
  organization_id?: number | null
  type?: CourseType
  level?: CourseLevel | null
  language?: LangCode
  cover_image_url?: string | null
  trailer_video_url?: string | null
  duration_weeks?: number | null
  estimated_hours?: number | null
  objectives?: string[]
  skills_gained?: string[]
  enrollment_type?: EnrollmentType
  max_students?: number | null
}

export interface Module {
  id: number
  course_id: number
  title: string
  description: string | null
  order_index: number
  available_from: string | null
  available_until: string | null
  created_at: string
}

export interface ModulePayload {
  title: string
  description?: string | null
  order_index?: number | null
  available_from?: string | null
  available_until?: string | null
}

export interface Lesson {
  id: number
  module_id: number
  title: string
  description: string | null
  order_index: number
  primary_content_id: number | null
  estimated_minutes: number | null
  is_required_for_completion: boolean
  created_at: string
}

export interface LessonPayload {
  title: string
  description?: string | null
  order_index?: number | null
  primary_content_id?: number | null
  estimated_minutes?: number | null
  is_required_for_completion?: boolean
}

export interface Enrollment {
  id: number
  course_id: number
  user_id: number
  enrolled_at: string
  enrollment_method: EnrollmentMethod
  enrolled_by: number | null
  completion_status: CompletionStatus
  completed_at: string | null
  final_grade: string | null
}

export interface EnrollmentStudent {
  enrollment_id: number
  user_id: number
  full_name: string
  email: string
  enrolled_at: string
  enrollment_method: EnrollmentMethod
  completion_status: CompletionStatus
  progress_percent: string  // Decimal as string
}

export interface PaginatedStudents {
  items: EnrollmentStudent[]
  total: number
}

export interface TeacherStudent {
  user_id: number
  full_name: string
  email: string | null
  avatar_url: string | null
  group_name: string | null
  course_count: number
  completed_count: number
  avg_grade: number | null
}

export interface PaginatedTeacherStudents {
  items: TeacherStudent[]
  total: number
}

export interface StudentCourseItem {
  course_id: number
  course_title: string
  progress_percent: number
  completion_status: CompletionStatus
  final_grade: number | null
  enrolled_at: string
}

export interface GradeDistribution {
  excellent: number
  good: number
  satisfactory: number
  fail: number
}

export interface CompletionBreakdown {
  in_progress: number
  completed: number
  failed: number
  dropped: number
}

export interface EnrollmentPoint {
  month: string
  count: number
}

export interface PerCourseStat {
  course_id: number
  title: string
  status: CourseStatus
  student_count: number
  completed_count: number
  completion_rate: number
  avg_grade: number | null
}

export interface TeacherAnalytics {
  total_courses: number
  published_courses: number
  total_students: number
  total_enrollments: number
  completion_rate: number
  avg_grade: number | null
  pending_grading: number
  grade_distribution: GradeDistribution
  completion_breakdown: CompletionBreakdown
  enrollments_over_time: EnrollmentPoint[]
  exam_attempts: number
  exam_pass_rate: number | null
  live_sessions_count: number
  per_course: PerCourseStat[]
}

export interface RoleCount {
  code: string
  name: string
  count: number
}

export interface TopCourseStat {
  course_id: number
  title: string
  status: CourseStatus
  enrollments: number
}

export interface PlatformAnalytics {
  total_users: number
  active_users: number
  users_by_role: RoleCount[]
  total_courses: number
  published_courses: number
  draft_courses: number
  archived_courses: number
  total_enrollments: number
  total_students: number
  completion_rate: number
  avg_grade: number | null
  completion_breakdown: CompletionBreakdown
  grade_distribution: GradeDistribution
  enrollments_over_time: EnrollmentPoint[]
  exam_attempts: number
  exam_pass_rate: number | null
  total_content: number
  total_live: number
  top_courses: TopCourseStat[]
}

export interface LessonProgress {
  id: number
  user_id: number
  lesson_id: number
  started_at: string | null
  completed_at: string | null
  progress_percent: string
  time_spent_seconds: number
  last_position: Record<string, unknown>
}

export interface CourseProgress {
  course_id: number
  enrolled: boolean
  completion_status: CompletionStatus | null
  completed_lessons: number
  total_required_lessons: number
  percent: string
  completed_at: string | null
}
