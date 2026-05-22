import { apiClient } from './client'
import type {
  LoginPayload,
  ProfileUpdatePayload,
  RegisterPayload,
  TokenResponse,
  TwoFactorEnableResponse,
  TwoFactorSetup,
  User,
} from '@shared/types/auth'

export const authApi = {
  async register(payload: RegisterPayload): Promise<User> {
    const { data } = await apiClient.post<User>('/auth/register', payload)
    return data
  },

  async login(payload: LoginPayload): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', payload)
    return data
  },

  async loginHemis(login: string, password: string): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/login/hemis', {
      login,
      password,
    })
    return data
  },

  // Phase 10e — HEMIS SSO callback
  async ssoHemis(ssoToken: string): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/sso/hemis', {
      sso_token: ssoToken,
    })
    return data
  },

  // Phase 10g — HEMIS tutor (pedagog) login
  async loginHemisTutor(
    login: string,
    password: string,
    recaptcha: string,
  ): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/login/hemis-tutor', {
      login,
      password,
      recaptcha,
    })
    return data
  },

  async logout(refreshToken: string): Promise<void> {
    await apiClient.post('/auth/logout', { refresh_token: refreshToken })
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me')
    return data
  },

  // --- Phase 2c: profile + avatar ---

  async getMe(): Promise<User> {
    const { data } = await apiClient.get<User>('/users/me')
    return data
  },

  async updateMe(payload: ProfileUpdatePayload): Promise<User> {
    const { data } = await apiClient.patch<User>('/users/me', payload)
    return data
  },

  async updatePreferences(prefs: Record<string, boolean>): Promise<User> {
    const { data } = await apiClient.patch<User>('/users/me/preferences', {
      notification_preferences: prefs,
    })
    return data
  },

  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await apiClient.post<{ avatar_url: string }>('/users/me/avatar', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async deleteAvatar(): Promise<void> {
    await apiClient.delete('/users/me/avatar')
  },

  // --- Phase 1d ---

  async forgotPassword(email: string): Promise<void> {
    await apiClient.post('/auth/forgot-password', { email })
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    })
  },

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await apiClient.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  },

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post('/auth/verify-email', { token })
  },

  async resendVerification(): Promise<void> {
    await apiClient.post('/auth/resend-verification')
  },

  // --- 2FA ---

  async setup2FA(): Promise<TwoFactorSetup> {
    const { data } = await apiClient.post<TwoFactorSetup>('/auth/2fa/setup')
    return data
  },

  async enable2FA(code: string): Promise<TwoFactorEnableResponse> {
    const { data } = await apiClient.post<TwoFactorEnableResponse>('/auth/2fa/enable', { code })
    return data
  },

  async disable2FA(password: string, code: string): Promise<void> {
    await apiClient.post('/auth/2fa/disable', { password, code })
  },
}
