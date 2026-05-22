// Assignments types — backend Pydantic schemalar bilan teng.

export type AssignmentType = 'essay' | 'file'
export type SubmissionStatus = 'submitted' | 'grading' | 'graded' | 'returned'
export type GradeLetter = 'A' | 'B' | 'C' | 'D' | 'F'

export interface Assignment {
  id: number
  course_id: number
  lesson_id: number | null
  title: string
  description: string | null
  instructions: string | null
  type: AssignmentType
  available_from: string | null
  due_date: string
  closed_at: string | null
  max_score: string  // Decimal as string
  pass_score: string | null
  weight_percent: string | null
  max_attempts: number
  late_submission_allowed: boolean
  late_penalty_per_day: string
  allowed_file_types: string[]
  max_file_size_mb: number
  is_published: boolean
  rubric_id: number | null
  plagiarism_check_enabled: boolean
  plagiarism_threshold: string
  peer_review_enabled: boolean
  peer_reviews_per_submission: number
  created_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedAssignments {
  items: Assignment[]
  total: number
}

export interface AssignmentPayload {
  course_id: number
  lesson_id?: number | null
  title: string
  description?: string | null
  instructions?: string | null
  type: AssignmentType
  available_from?: string | null
  due_date: string
  closed_at?: string | null
  max_score?: string | number
  pass_score?: string | number | null
  weight_percent?: string | number | null
  max_attempts?: number
  late_submission_allowed?: boolean
  late_penalty_per_day?: string | number
  allowed_file_types?: string[]
  max_file_size_mb?: number
  is_published?: boolean
  rubric_id?: number | null
  plagiarism_check_enabled?: boolean
  plagiarism_threshold?: string | number
  peer_review_enabled?: boolean
  peer_reviews_per_submission?: number
}

export interface SubmissionFile {
  name: string
  url: string
  mime: string
  size: number
}

export interface Submission {
  id: number
  assignment_id: number
  user_id: number
  user_full_name: string | null
  user_email: string | null
  attempt_number: number
  content: string | null
  files: SubmissionFile[]
  submitted_at: string
  is_late: boolean
  days_late: number
  status: SubmissionStatus
  score: string | null
  final_score: string | null
  grade_letter: GradeLetter | null
  feedback: string | null
  rubric_scores: Record<string, number>
  annotations: Array<Record<string, unknown>>
  plagiarism_score: string | null
  plagiarism_report_url: string | null
  plagiarism_flagged: boolean
  plagiarism_checked_at: string | null
  graded_by: number | null
  graded_by_full_name: string | null
  graded_at: string | null
}

// ============================================================================
// Peer review (Phase 4e)
// ============================================================================

export interface PeerReview {
  id: number
  submission_id: number
  reviewer_id: number
  score: string | null
  feedback: string | null
  rubric_scores: Record<string, number>
  submitted_at: string | null
  created_at: string
}

export interface PeerReviewSubmitPayload {
  score?: string | number
  rubric_scores?: Record<string, number>
  feedback?: string | null
}

// ============================================================================
// Appeals (Phase 4e)
// ============================================================================

export type AppealStatus = 'pending' | 'approved' | 'rejected'

export interface Appeal {
  id: number
  submission_id: number
  student_id: number
  student_full_name: string | null
  student_email: string | null
  reason: string
  status: AppealStatus
  new_score: string | null
  response: string | null
  reviewed_by: number | null
  reviewed_by_full_name: string | null
  reviewed_at: string | null
  created_at: string
}

export interface AppealCreatePayload {
  reason: string
}

export interface AppealRespondPayload {
  status: 'approved' | 'rejected'
  new_score?: string | number | null
  response?: string | null
}

export interface PaginatedAppeals {
  items: Appeal[]
  total: number
}

// ============================================================================
// Plagiarism (Phase 4e)
// ============================================================================

export interface PlagiarismCheckResult {
  submission_id: number
  plagiarism_score: string | null
  plagiarism_report_url: string | null
  plagiarism_flagged: boolean
  plagiarism_checked_at: string | null
}

export interface SubmissionUploadResponse {
  name: string
  url: string
  mime: string
  size: number
}

export interface SubmissionCreatePayload {
  content?: string | null
  files?: SubmissionFile[]
}

// ============================================================================
// Rubrics
// ============================================================================

export interface RubricLevel {
  label: string
  points: string | number
  description?: string | null
}

export interface RubricCriterion {
  key: string
  name: string
  max_points: string | number
  levels?: RubricLevel[]
}

export interface Rubric {
  id: number
  title: string
  description: string | null
  total_points: string
  criteria: RubricCriterion[]
  organization_id: number | null
  created_by: number
  created_at: string
  updated_at: string
}

export interface PaginatedRubrics {
  items: Rubric[]
  total: number
}

// ============================================================================
// Grading
// ============================================================================

export interface GradePayload {
  score?: string | number
  rubric_scores?: Record<string, number>
  grade_letter?: GradeLetter
  feedback?: string | null
  return_for_revision?: boolean
}

export interface AnnotationItem {
  page?: number
  x?: number
  y?: number
  w?: number
  h?: number
  text: string
  color?: string
}
