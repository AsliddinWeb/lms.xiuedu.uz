import { apiClient } from './client'
import type {
  AcademicCalendar,
  Curriculum,
  Department,
  Faculty,
  Organization,
  OrganizationCreatePayload,
  Paginated,
  Specialty,
  Subject,
} from '@shared/types/academic'

export const orgsApi = {
  async list(q?: string): Promise<Organization[]> {
    const { data } = await apiClient.get<Organization[]>('/organizations', {
      params: { q, page_size: 200 },
    })
    return data
  },
  async update(id: number, payload: Partial<OrganizationCreatePayload>): Promise<Organization> {
    const { data } = await apiClient.patch<Organization>(`/organizations/${id}`, payload)
    return data
  },
}

export const facultiesApi = {
  async list(params: {
    organization_id?: number
    is_active?: boolean
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<Paginated<Faculty>> {
    const { data } = await apiClient.get<Paginated<Faculty>>('/faculties', { params })
    return data
  },
  async create(payload: Omit<Faculty, 'id' | 'created_at'>): Promise<Faculty> {
    return (await apiClient.post<Faculty>('/faculties', payload)).data
  },
  async update(id: number, payload: Partial<Omit<Faculty, 'id' | 'created_at'>>): Promise<Faculty> {
    return (await apiClient.patch<Faculty>(`/faculties/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/faculties/${id}`)
  },
}

export const departmentsApi = {
  async list(params: {
    faculty_id?: number
    organization_id?: number
    is_active?: boolean
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<Paginated<Department>> {
    const { data } = await apiClient.get<Paginated<Department>>('/departments', { params })
    return data
  },
  async create(payload: Omit<Department, 'id' | 'created_at'>): Promise<Department> {
    return (await apiClient.post<Department>('/departments', payload)).data
  },
  async update(id: number, payload: Partial<Omit<Department, 'id' | 'created_at'>>): Promise<Department> {
    return (await apiClient.patch<Department>(`/departments/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/departments/${id}`)
  },
}

export const specialtiesApi = {
  async list(params: {
    department_id?: number
    level?: string
    distance_only?: boolean
    is_active?: boolean
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<Paginated<Specialty>> {
    const { data } = await apiClient.get<Paginated<Specialty>>('/specialties', { params })
    return data
  },
  async create(payload: Omit<Specialty, 'id' | 'created_at'>): Promise<Specialty> {
    return (await apiClient.post<Specialty>('/specialties', payload)).data
  },
  async update(id: number, payload: Partial<Omit<Specialty, 'id' | 'created_at'>>): Promise<Specialty> {
    return (await apiClient.patch<Specialty>(`/specialties/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/specialties/${id}`)
  },
  async enableDistance(id: number): Promise<Specialty> {
    return (await apiClient.post<Specialty>(`/specialties/${id}/enable-distance`)).data
  },
}

export const subjectsApi = {
  async list(params: {
    department_id?: number
    language?: string
    is_active?: boolean
    q?: string
    page?: number
    page_size?: number
  } = {}): Promise<Paginated<Subject>> {
    const { data } = await apiClient.get<Paginated<Subject>>('/subjects', { params })
    return data
  },
  async create(payload: {
    department_id: number
    code: string
    name: string
    short_name?: string | null
    description?: string | null
    credits: number
    lecture_hours?: number
    practice_hours?: number
    seminar_hours?: number
    self_study_hours?: number
    language?: string
    prerequisite_ids?: number[]
    is_active?: boolean
  }): Promise<Subject> {
    return (await apiClient.post<Subject>('/subjects', payload)).data
  },
  async update(id: number, payload: Partial<Omit<Subject, 'id' | 'created_at'>>): Promise<Subject> {
    return (await apiClient.patch<Subject>(`/subjects/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/subjects/${id}`)
  },
}

export const curriculaApi = {
  async list(params: {
    specialty_id?: number
    is_active?: boolean
    page?: number
    page_size?: number
  } = {}): Promise<Paginated<Curriculum>> {
    const { data } = await apiClient.get<Paginated<Curriculum>>('/curricula', { params })
    return data
  },
  async create(payload: {
    specialty_id: number
    name: string
    version?: string | null
    valid_from: string
    valid_until?: string | null
    based_on?: string | null
    standard_code?: string | null
    total_credits: number
    subjects?: Array<{ subject_id: number; semester: number; is_required: boolean }>
  }): Promise<Curriculum> {
    return (await apiClient.post<Curriculum>('/curricula', payload)).data
  },
  async update(id: number, payload: Partial<Curriculum>): Promise<Curriculum> {
    return (await apiClient.patch<Curriculum>(`/curricula/${id}`, payload)).data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/curricula/${id}`)
  },
  async clone(id: number, newVersion: string, newValidFrom: string): Promise<Curriculum> {
    const { data } = await apiClient.post<Curriculum>(`/curricula/${id}/clone`, {
      new_version: newVersion,
      new_valid_from: newValidFrom,
    })
    return data
  },
  async approve(id: number): Promise<Curriculum> {
    return (await apiClient.post<Curriculum>(`/curricula/${id}/approve`)).data
  },
}

export const calendarsApi = {
  async list(organization_id?: number): Promise<AcademicCalendar[]> {
    const { data } = await apiClient.get<AcademicCalendar[]>('/academic-calendars', {
      params: { organization_id },
    })
    return data
  },
  async getCurrent(organization_id: number): Promise<AcademicCalendar | null> {
    const { data } = await apiClient.get<AcademicCalendar | null>(
      '/academic-calendars/current',
      { params: { organization_id } },
    )
    return data
  },
}
