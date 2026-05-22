import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'

const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: 30_000,
})

// LocalStorage keys — auth store ham shu kalitlardan foydalanadi.
export const TOKEN_KEYS = {
  access: 'lms.access_token',
  refresh: 'lms.refresh_token',
} as const

// ---------- Request interceptor: Bearer token ----------

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem(TOKEN_KEYS.access)
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---------- Response interceptor: 401 → refresh + retry ----------

let refreshPromise: Promise<string> | null = null

async function tryRefresh(): Promise<string> {
  const refreshToken = localStorage.getItem(TOKEN_KEYS.refresh)
  if (!refreshToken) throw new Error('no_refresh_token')

  const { data } = await axios.post<{ access_token: string; refresh_token: string }>(
    `${API_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { withCredentials: true },
  )
  localStorage.setItem(TOKEN_KEYS.access, data.access_token)
  localStorage.setItem(TOKEN_KEYS.refresh, data.refresh_token)
  return data.access_token
}

apiClient.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined

    // Refresh endpointini o'zi 401 qaytsa — qayta urinmaymiz.
    const isRefreshCall = original?.url?.includes('/auth/refresh')
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isRefreshCall &&
      localStorage.getItem(TOKEN_KEYS.refresh)
    ) {
      original._retry = true
      try {
        if (!refreshPromise) refreshPromise = tryRefresh()
        const newToken = await refreshPromise
        refreshPromise = null
        if (original.headers) original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      } catch (refreshErr) {
        refreshPromise = null
        // Refresh ham yiqildi → tokenlarni tozalash, login sahifasiga o'tkazish.
        localStorage.removeItem(TOKEN_KEYS.access)
        localStorage.removeItem(TOKEN_KEYS.refresh)
        window.dispatchEvent(new CustomEvent('lms:logout', { detail: 'refresh_failed' }))
        return Promise.reject(refreshErr)
      }
    }
    return Promise.reject(error)
  },
)

// ---------- Helper: API xatoligidan inson o'qiy oladigan xabar olish ----------

export function extractErrorMessage(err: unknown, fallback = 'Xatolik yuz berdi'): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      return first?.msg ?? fallback
    }
  }
  return fallback
}

/** Axios xatosi 404 (Not Found) bo'lsa true qaytaradi — detail view'larda
 *  yo'q resource uchun parent listga redirect qilishda ishlatiladi. */
export function isNotFound(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response?.status === 404
}
