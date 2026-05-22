// Academic structure types — backend Pydantic schemalar bilan teng.

export interface Organization {
  id: number
  code: string
  name: string
  short_name: string | null
  type: 'state' | 'private' | 'foreign' | null
  license_number: string | null
  rector_id: number | null
  address: string | null
  phone: string | null
  email: string | null
  website: string | null
  domain: string | null
  logo_url: string | null
  branding: Record<string, unknown>
  settings: Record<string, unknown>
  is_active: boolean
  created_at: string
}

export type OrganizationCreatePayload = Partial<
  Omit<Organization, 'id' | 'created_at'>
> & {
  code: string
  name: string
}

export interface Faculty {
  id: number
  organization_id: number
  code: string
  name: string
  short_name: string | null
  dean_id: number | null
  is_active: boolean
  created_at: string
}

export interface Department {
  id: number
  faculty_id: number
  code: string
  name: string
  head_id: number | null
  is_active: boolean
  created_at: string
}

export type EducationLevel = 'bachelor' | 'master' | 'phd'
export type EducationForm = 'fulltime' | 'parttime' | 'evening' | 'distance'
export type LanguageCode = 'uz-lat' | 'uz-cyr' | 'ru' | 'en'

export interface Specialty {
  id: number
  department_id: number
  code: string
  name: string
  level: EducationLevel
  duration_years: number
  education_form: EducationForm
  language: LanguageCode
  distance_enabled: boolean
  annual_quota: number | null
  is_active: boolean
  created_at: string
}

export interface Subject {
  id: number
  department_id: number
  code: string
  name: string
  short_name: string | null
  description: string | null
  credits: number
  lecture_hours: number
  practice_hours: number
  seminar_hours: number
  self_study_hours: number
  language: LanguageCode
  prerequisite_ids: number[]
  is_active: boolean
  created_at: string
}

export interface CurriculumSubject {
  id: number
  curriculum_id: number
  subject_id: number
  semester: number
  is_required: boolean
}

export interface Curriculum {
  id: number
  specialty_id: number
  name: string
  version: string | null
  valid_from: string
  valid_until: string | null
  based_on: string | null
  standard_code: string | null
  total_credits: number
  is_active: boolean
  approved_by: number | null
  approved_at: string | null
  created_at: string
  subjects: CurriculumSubject[]
}

export interface AcademicCalendar {
  id: number
  organization_id: number
  academic_year: string
  name: string
  start_date: string
  end_date: string
  semesters: Array<Record<string, unknown>>
  holidays: Array<Record<string, unknown>>
  is_active: boolean
}

export interface Paginated<T> {
  items: T[]
  total: number
}
