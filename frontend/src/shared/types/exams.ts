// Phase 6 — Exams type'lari

export type ExamType = 'midterm' | 'final' | 'quiz' | 'dak'
export type ExamStatus = 'draft' | 'published' | 'archived'

export type QuestionType =
  | 'single_choice'
  | 'multiple_choice'
  | 'true_false'
  | 'short_text'
  | 'essay'
  | 'code'
  | 'file_upload'

export type AttemptStatus =
  | 'in_progress'
  | 'submitted'
  | 'auto_submitted'
  | 'graded'
  | 'flagged'
  | 'invalidated'

export interface QuestionOptionPayload {
  text: string
  is_correct: boolean
  explanation?: string | null
  order_index: number
}

export interface QuestionOptionPublic extends QuestionOptionPayload {
  id: number
}

export interface QuestionOptionStudent {
  id: number
  text: string
  order_index: number
}

export interface QuestionBase {
  type: QuestionType
  title: string
  explanation?: string | null
  points: string | number
  required: boolean
  order_index: number

  code_language?: string | null
  code_initial?: string | null
  max_file_size_mb?: number | null
  allowed_file_types?: string[] | null

  exact_match: boolean
  case_sensitive: boolean
  correct_text?: string | null
  alternative_answers?: string[] | null

  options?: QuestionOptionPayload[]
}

export interface QuestionPayload extends QuestionBase {}

export interface QuestionPublic extends QuestionBase {
  id: number
  exam_id: number
  options: QuestionOptionPublic[]
  created_at: string
  updated_at: string
}

export interface QuestionStudent {
  id: number
  exam_id: number
  type: QuestionType
  title: string
  points: string
  required: boolean
  order_index: number
  code_language?: string | null
  code_initial?: string | null
  max_file_size_mb?: number | null
  allowed_file_types?: string[] | null
  options: QuestionOptionStudent[]
}

export interface ExamPayload {
  course_id: number
  lesson_id?: number | null
  title: string
  description?: string | null
  type: ExamType
  duration_minutes: number
  max_attempts: number
  passing_score: string | number
  shuffle_questions: boolean
  shuffle_options: boolean
  show_correct_answers: boolean
  question_count?: number | null
  proctoring_enabled: boolean
  require_face_id: boolean
  require_screen_share: boolean
  allow_tab_switch: boolean
  max_face_loss_seconds: number
  available_from?: string | null
  available_until?: string | null
}

export interface ExamUpdatePayload extends Partial<Omit<ExamPayload, 'course_id'>> {}

export interface Exam {
  id: number
  course_id: number
  lesson_id: number | null
  organization_id: number | null
  title: string
  description: string | null
  type: ExamType
  status: ExamStatus
  duration_minutes: number
  max_attempts: number
  passing_score: string
  shuffle_questions: boolean
  shuffle_options: boolean
  show_correct_answers: boolean
  question_count: number | null
  proctoring_enabled: boolean
  require_face_id: boolean
  require_screen_share: boolean
  allow_tab_switch: boolean
  max_face_loss_seconds: number
  available_from: string | null
  available_until: string | null
  closed_at: string | null
  created_by: number
  created_at: string
  updated_at: string
  total_questions: number
  total_points: string
}

export interface PaginatedExams {
  items: Exam[]
  total: number
}

// ---- Attempts ----

export interface AnswerSubmit {
  question_id: number
  selected_option_ids?: number[] | null
  text_answer?: string | null
  code_answer?: string | null
  file_url?: string | null
  file_size_bytes?: number | null
}

export interface AnswerPublic {
  id: number
  attempt_id: number
  question_id: number
  selected_option_ids: number[] | null
  text_answer: string | null
  code_answer: string | null
  file_url: string | null
  file_size_bytes: number | null
  auto_correct: boolean | null
  points_earned: string
  points_max: string | null
  graded_by: number | null
  graded_at: string | null
  grader_comment: string | null
  // Phase 9e — plagiat
  plagiarism_score: string | null
  plagiarism_match_answer_id: number | null
  plagiarism_checked_at: string | null
  created_at: string
  updated_at: string
}

export interface AttemptStudentSummary {
  id: number
  exam_id: number
  attempt_number: number
  status: AttemptStatus
  started_at: string
  submitted_at: string | null
  deadline_at: string
  time_spent_seconds: number
  total_score: string | null
  max_score: string | null
  percentage: string | null
  passed: boolean | null
}

export interface AttemptTakeView {
  id: number
  exam_id: number
  attempt_number: number
  status: AttemptStatus
  started_at: string
  deadline_at: string
  duration_minutes: number
  questions: QuestionStudent[]
  saved_answers: AnswerSubmit[]
}

export interface AttemptResult {
  id: number
  exam_id: number
  attempt_number: number
  status: AttemptStatus
  submitted_at: string | null
  time_spent_seconds: number
  auto_score: string | null
  manual_score: string | null
  total_score: string | null
  max_score: string | null
  percentage: string | null
  passed: boolean | null
  answers: AnswerPublic[]
}

export interface SmartFlag {
  type: string
  weight: number
  detail: string
}

export interface AttemptPublic {
  id: number
  exam_id: number
  user_id: number
  attempt_number: number
  status: AttemptStatus
  started_at: string
  submitted_at: string | null
  deadline_at: string
  time_spent_seconds: number
  auto_score: string | null
  manual_score: string | null
  total_score: string | null
  max_score: string | null
  percentage: string | null
  passed: boolean | null
  violation_score: number
  flagged: boolean
  // Phase 9f
  smart_score: number
  smart_flags: SmartFlag[] | null
  created_at: string
  updated_at: string
}

export interface PaginatedAttempts {
  items: AttemptPublic[]
  total: number
}

// Phase 9d — Code test cases
export interface CodeTestCase {
  id: number
  question_id: number
  order_index: number
  stdin: string
  expected_stdout: string
  is_hidden: boolean
  weight: string
  created_at: string
  updated_at: string
}

export interface CodeTestCasePayload {
  stdin?: string
  expected_stdout: string
  is_hidden?: boolean
  weight?: number
  order_index?: number | null
}

export interface CodeRunResultItem {
  test_case_id: number
  is_hidden: boolean
  passed: boolean
  stdout: string
  stderr: string
  exit_code: number
  runtime_ms: number
  timed_out: boolean
  expected_stdout: string | null
}

export interface CodeRunResponse {
  results: CodeRunResultItem[]
  passed_count: number
  total: number
}

export interface GradeAnswerEntry {
  answer_id: number
  points_earned: string | number
  grader_comment?: string | null
}

export interface GradeAttemptPayload {
  grades: GradeAnswerEntry[]
}
