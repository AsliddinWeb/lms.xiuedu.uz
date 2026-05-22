export interface User {
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
  permissions: string[]
  hemis_id?: number | null
  profile?: ProfilePublic | null
  created_at?: string
}

export interface ProfilePublic {
  pinfl: string | null
  passport_series: string | null
  passport_number: string | null
  birthdate: string | null
  gender: string | null
  nationality: string | null
  address: string | null
  bio: string | null
  language: string
  timezone: string
  notification_preferences: Record<string, boolean>
}

export interface ProfileUpdatePayload {
  full_name?: string
  phone?: string | null
  pinfl?: string | null
  passport_series?: string | null
  passport_number?: string | null
  birthdate?: string | null
  gender?: string | null
  nationality?: string | null
  address?: string | null
  bio?: string | null
  language?: string | null
  timezone?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface LoginPayload {
  email?: string
  phone?: string
  password: string
  totp_code?: string
}

export interface RegisterPayload {
  email: string
  password: string
  full_name: string
  phone?: string
}

export interface ApiError {
  detail: string | { type: string; loc: string[]; msg: string; ctx?: { reason?: string } }[]
  code?: string
}

// --- Phase 1d ---

export interface TwoFactorSetup {
  secret: string
  otpauth_uri: string
  qr_png_base64: string
}

export interface TwoFactorEnableResponse {
  backup_codes: string[]
}
