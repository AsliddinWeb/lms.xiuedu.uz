<script setup lang="ts">
/**
 * Phase 15 — HEMIS OAuth2 callback handler.
 *
 * Oqim:
 *   1. Talaba/o'qituvchi LoginView'da "HEMIS orqali kirish" → dropdown → "Talaba" / "O'qituvchi"
 *   2. Backend authorize URL qaytaradi, frontend window.location.href = URL
 *   3. Foydalanuvchi HEMIS portalida login qiladi
 *   4. HEMIS bizga redirect: `https://lms.xiuedu.uz/auth/hemis/callback?code=...&state=...`
 *   5. Bu view code+state ni backend'ga POST qiladi
 *   6. Backend code -> access_token -> userinfo -> user upsert -> LMS JWT
 *   7. Frontend tokenni saqlaydi va /app/dashboard'ga redirect qiladi
 */

import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const status = ref<'loading' | 'success' | 'error'>('loading')
const errorMsg = ref<string | null>(null)
let started = false

async function handleCallback() {
  if (started) return
  started = true

  const code = (route.query.code as string) || ''
  const state = (route.query.state as string) || ''

  if (!code || !state) {
    status.value = 'error'
    errorMsg.value = t('auth.oauth_missing_params')
    return
  }

  try {
    await auth.hemisOAuthCallback(code, state)
    status.value = 'success'
    setTimeout(() => {
      const redirect = (route.query.redirect as string) || '/app/dashboard'
      router.replace(redirect)
    }, 400)
  } catch {
    status.value = 'error'
    errorMsg.value = auth.error || t('auth.oauth_callback_failed')
  }
}

onMounted(handleCallback)
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] max-w-md">
        HEMIS OAuth
      </h2>
      <p class="opacity-60 max-w-sm leading-relaxed text-sm mt-6">
        {{ t('auth.oauth_side_desc') }}
      </p>
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">HEMIS OAUTH · CALLBACK</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">
        {{ t('auth.oauth_callback_title') }}
      </h1>
      <p class="text-muted-foreground text-sm">
        {{ t('auth.oauth_callback_subtitle') }}
      </p>
    </div>

    <div v-if="status === 'loading'" class="py-12 text-center">
      <div class="inline-block animate-spin rounded-full h-10 w-10 border-2 border-foreground border-t-transparent mb-4"></div>
      <p class="text-[13px] text-muted-foreground">{{ t('auth.oauth_validating') }}</p>
    </div>

    <div v-else-if="status === 'success'" class="py-12 text-center">
      <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-success-500/15 text-success-600 mb-4">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 6 9 17l-5-5" />
        </svg>
      </div>
      <p class="text-[14px] font-medium text-foreground mb-1">
        {{ t('auth.oauth_success_title') }}
      </p>
      <p class="text-[12px] text-muted-foreground">{{ t('auth.oauth_success_subtitle') }}</p>
    </div>

    <div v-else>
      <UiAlert variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
      <RouterLink :to="{ name: 'login' }" class="block">
        <UiButton variant="outline" full-width type="button">
          {{ t('auth.sso_back_to_login') }}
        </UiButton>
      </RouterLink>
    </div>
  </UiAuthLayout>
</template>
