/**
 * Phase 7e — Frontend Sentry SDK.
 *
 * `VITE_SENTRY_DSN` o'rnatilgan bo'lsa, Sentry'ga ulanadi.
 * Aks holda silent — production'da dasturchi ko'rmaydigan xato yo'q.
 */

import type { App } from 'vue'
import type { Router } from 'vue-router'

import * as Sentry from '@sentry/vue'

export function initSentry(app: App, router: Router, appName: 'user' | 'admin'): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
  if (!dsn) return

  const env = (import.meta.env.VITE_APP_ENV as string | undefined) ?? 'development'
  const release = (import.meta.env.VITE_APP_VERSION as string | undefined) ?? 'unknown'

  Sentry.init({
    app,
    dsn,
    environment: `${env}-${appName}`,
    release,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0.1,
  })
}
