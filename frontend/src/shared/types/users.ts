export interface UserListItem {
  id: number
  email: string
  full_name: string
  phone: string | null
  avatar_url: string | null
  is_active: boolean
  is_verified: boolean
  is_2fa_enabled: boolean
  last_login_at: string | null
  tenant_id: number | null
  roles: string[]
  created_at: string
}

export interface UserDetail extends UserListItem {
  permissions: string[]
}

export interface PaginatedUsers {
  items: UserListItem[]
  total: number
  page: number
  page_size: number
}

export interface UserCreatePayload {
  email: string
  password: string
  full_name: string
  phone?: string
  is_active?: boolean
  is_verified?: boolean
  tenant_id?: number | null
  role_codes?: string[]
}

export interface UserUpdatePayload {
  full_name?: string
  phone?: string | null
  is_active?: boolean
  is_verified?: boolean
  tenant_id?: number | null
  avatar_url?: string | null
}

export interface UsersListQuery {
  q?: string
  role?: string
  is_active?: boolean
  tenant_id?: number
  page?: number
  page_size?: number
}

// --- Roles ---

export interface Permission {
  id: number
  code: string
  name: string
  description: string | null
  category: string | null
}

export interface Role {
  id: number
  code: string
  name: string
  description: string | null
  is_system: boolean
  tenant_id: number | null
  permissions: Permission[]
}
