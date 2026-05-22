import { defineStore } from 'pinia'
import { ref } from 'vue'

import { rolesApi } from '@shared/api/roles'
import { usersApi } from '@shared/api/users'
import { extractErrorMessage } from '@shared/api/client'
import type {
  PaginatedUsers,
  Role,
  UserCreatePayload,
  UserDetail,
  UserUpdatePayload,
  UsersListQuery,
} from '@shared/types/users'

export const useUsersStore = defineStore('admin-users', () => {
  const list = ref<PaginatedUsers>({ items: [], total: 0, page: 1, page_size: 20 })
  const roles = ref<Role[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchList(query: UsersListQuery): Promise<void> {
    loading.value = true
    error.value = null
    try {
      list.value = await usersApi.list(query)
    } catch (e) {
      error.value = extractErrorMessage(e, "Foydalanuvchilarni yuklashda xato")
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchRoles(): Promise<void> {
    if (roles.value.length > 0) return
    roles.value = await rolesApi.list()
  }

  async function create(payload: UserCreatePayload): Promise<UserDetail> {
    error.value = null
    try {
      return await usersApi.create(payload)
    } catch (e) {
      error.value = extractErrorMessage(e, 'Yaratishda xato')
      throw e
    }
  }

  async function update(id: number, payload: UserUpdatePayload): Promise<UserDetail> {
    return await usersApi.update(id, payload)
  }

  async function remove(id: number): Promise<void> {
    await usersApi.remove(id)
  }

  async function activate(id: number): Promise<UserDetail> {
    return await usersApi.activate(id)
  }

  async function deactivate(id: number): Promise<UserDetail> {
    return await usersApi.deactivate(id)
  }

  async function replaceRoles(id: number, codes: string[]): Promise<void> {
    await usersApi.replaceRoles(id, codes)
  }

  return {
    list,
    roles,
    loading,
    error,
    fetchList,
    fetchRoles,
    create,
    update,
    remove,
    activate,
    deactivate,
    replaceRoles,
  }
})
