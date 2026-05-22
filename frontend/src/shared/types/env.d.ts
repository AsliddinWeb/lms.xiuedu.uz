/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_CDN_URL: string
  readonly VITE_APP_URL: string
  readonly VITE_ADMIN_URL: string
  readonly VITE_DEFAULT_LOCALE: string
  readonly VITE_AVAILABLE_LOCALES: string
  readonly VITE_ONEID_CLIENT_ID: string
  readonly VITE_ONEID_REDIRECT_URI: string
  readonly VITE_ONEID_AUTHORIZE_URL: string
  readonly VITE_SENTRY_DSN: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
