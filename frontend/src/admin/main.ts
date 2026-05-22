import { createApp } from 'vue'
import { createPinia } from 'pinia'

import { vPermission } from '@shared/directives/permission'
import { i18n } from '@shared/i18n'
import { initSentry } from '@shared/observability/sentry'
import { useLocaleStore } from '@shared/stores/locale'
import { useThemeStore } from '@shared/stores/theme'
import App from './App.vue'
import { router } from './router'
import '@shared/styles/main.css'

const app = createApp(App)
initSentry(app, router, 'admin')
app.use(createPinia())

useThemeStore()
useLocaleStore()

app.use(i18n)
app.directive('permission', vPermission)
app.use(router)
app.mount('#app')
