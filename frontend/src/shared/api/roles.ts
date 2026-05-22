import { apiClient } from './client'
import type { Permission, Role } from '@shared/types/users'

export const rolesApi = {
  async list(): Promise<Role[]> {
    const { data } = await apiClient.get<Role[]>('/roles')
    return data
  },

  async listPermissions(): Promise<Permission[]> {
    const { data } = await apiClient.get<Permission[]>('/permissions')
    return data
  },
}
