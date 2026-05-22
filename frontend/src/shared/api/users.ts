import { apiClient } from './client'
import type {
  PaginatedUsers,
  UserCreatePayload,
  UserDetail,
  UserUpdatePayload,
  UsersListQuery,
} from '@shared/types/users'

export const usersApi = {
  async list(query: UsersListQuery = {}): Promise<PaginatedUsers> {
    const { data } = await apiClient.get<PaginatedUsers>('/users', { params: query })
    return data
  },

  async get(id: number): Promise<UserDetail> {
    const { data } = await apiClient.get<UserDetail>(`/users/${id}`)
    return data
  },

  async create(payload: UserCreatePayload): Promise<UserDetail> {
    const { data } = await apiClient.post<UserDetail>('/users', payload)
    return data
  },

  async update(id: number, payload: UserUpdatePayload): Promise<UserDetail> {
    const { data } = await apiClient.patch<UserDetail>(`/users/${id}`, payload)
    return data
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/users/${id}`)
  },

  async activate(id: number): Promise<UserDetail> {
    const { data } = await apiClient.post<UserDetail>(`/users/${id}/activate`)
    return data
  },

  async deactivate(id: number): Promise<UserDetail> {
    const { data } = await apiClient.post<UserDetail>(`/users/${id}/deactivate`)
    return data
  },

  async setPassword(id: number, password: string): Promise<void> {
    await apiClient.post(`/users/${id}/set-password`, { password })
  },

  async replaceRoles(id: number, roleCodes: string[]): Promise<void> {
    await apiClient.put(`/users/${id}/roles`, roleCodes)
  },
}
