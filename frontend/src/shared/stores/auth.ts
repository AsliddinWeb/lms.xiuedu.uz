import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { TOKEN_KEYS, extractErrorMessage } from '@shared/api/client'
import { authApi } from '@shared/api/auth'
import type { LoginPayload, RegisterPayload, User } from '@shared/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem(TOKEN_KEYS.access))
  const refreshToken = ref<string | null>(localStorage.getItem(TOKEN_KEYS.refresh))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const roles = computed(() => user.value?.roles ?? [])
  const permissions = computed(() => user.value?.permissions ?? [])

  function _saveTokens(access: string, refresh: string): void {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(TOKEN_KEYS.access, access)
    localStorage.setItem(TOKEN_KEYS.refresh, refresh)
  }

  function _clearTokens(): void {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEYS.access)
    localStorage.removeItem(TOKEN_KEYS.refresh)
  }

  async function login(payload: LoginPayload): Promise<User> {
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.login(payload)
      _saveTokens(tokens.access_token, tokens.refresh_token)
      const me = await authApi.me()
      user.value = me
      return me
    } catch (err) {
      error.value = extractErrorMessage(err, 'Kirish amalga oshmadi')
      _clearTokens()
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loginHemis(hemisLogin: string, hemisPassword: string): Promise<User> {
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.loginHemis(hemisLogin, hemisPassword)
      _saveTokens(tokens.access_token, tokens.refresh_token)
      const me = await authApi.me()
      user.value = me
      return me
    } catch (err) {
      error.value = extractErrorMessage(err, 'HEMIS orqali kirish amalga oshmadi')
      _clearTokens()
      throw err
    } finally {
      loading.value = false
    }
  }

  // Phase 10e — SSO callback: HEMIS-dan kelgan sso_token-ni almashtirib LMS JWT olish
  async function ssoHemis(ssoToken: string): Promise<User> {
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.ssoHemis(ssoToken)
      _saveTokens(tokens.access_token, tokens.refresh_token)
      const me = await authApi.me()
      user.value = me
      return me
    } catch (err) {
      error.value = extractErrorMessage(err, 'HEMIS SSO token yaroqsiz')
      _clearTokens()
      throw err
    } finally {
      loading.value = false
    }
  }

  // Phase 15 — HEMIS OAuth callback: code+state ni LMS JWT'ga almashtirish
  async function hemisOAuthCallback(code: string, state: string): Promise<User> {
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.hemisOAuthCallback(code, state)
      _saveTokens(tokens.access_token, tokens.refresh_token)
      const me = await authApi.me()
      user.value = me
      return me
    } catch (err) {
      error.value = extractErrorMessage(err, 'HEMIS OAuth callback xato')
      _clearTokens()
      throw err
    } finally {
      loading.value = false
    }
  }

  // Phase 10g — HEMIS pedagog login (reCAPTCHA bilan)
  async function loginHemisTutor(
    tutorLogin: string,
    tutorPassword: string,
    recaptcha: string,
  ): Promise<User> {
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.loginHemisTutor(tutorLogin, tutorPassword, recaptcha)
      _saveTokens(tokens.access_token, tokens.refresh_token)
      const me = await authApi.me()
      user.value = me
      return me
    } catch (err) {
      error.value = extractErrorMessage(err, 'HEMIS pedagog kirishi amalga oshmadi')
      _clearTokens()
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<User> {
    loading.value = true
    error.value = null
    try {
      return await authApi.register(payload)
    } catch (err) {
      error.value = extractErrorMessage(err, "Ro'yxatdan o'tish amalga oshmadi")
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    if (refreshToken.value) {
      try {
        await authApi.logout(refreshToken.value)
      } catch {
        /* server xato bersa ham lokalda chiqamiz */
      }
    }
    _clearTokens()
  }

  async function fetchMe(): Promise<User | null> {
    if (!accessToken.value) return null
    try {
      const me = await authApi.me()
      user.value = me
      return me
    } catch {
      _clearTokens()
      return null
    }
  }

  function hasRole(code: string): boolean {
    return roles.value.includes(code)
  }

  function hasAnyRole(codes: string[]): boolean {
    return codes.some((c) => roles.value.includes(c))
  }

  function hasPermission(perm: string): boolean {
    return permissions.value.some((g) => {
      if (g === perm) return true
      if (g === 'platform.*') return true
      if (g.endsWith('.*')) return perm.startsWith(g.slice(0, -2) + '.')
      return false
    })
  }

  return {
    // state
    user,
    accessToken,
    refreshToken,
    loading,
    error,
    // computed
    isAuthenticated,
    roles,
    permissions,
    // actions
    login,
    loginHemis,
    ssoHemis,
    hemisOAuthCallback,
    loginHemisTutor,
    register,
    logout,
    fetchMe,
    hasRole,
    hasAnyRole,
    hasPermission,
  }
})
