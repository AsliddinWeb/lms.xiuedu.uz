<script setup lang="ts">
/**
 * Phase 10e — HEMIS SSO callback handler.
 *
 * Flow:
 *   1. Talaba HEMIS portalida login bo'lib turibdi
 *   2. HEMIS portalda "LMS'ga o'tish" tugmasi → bizga 302 redirect
 *      `https://lms.xiuedu.uz/auth/sso/callback?sso_token=...`
 *   3. Bu view sso_token-ni URL query'dan oladi
 *   4. POST /api/v1/auth/sso/hemis { sso_token } bilan backend'ga yuboriladi
 *   5. Backend HEMIS-ga validate qilib, LMS JWT chiqaradi
 *   6. Bu view JWT'ni saqlaydi va `/app/dashboard`-ga redirect qiladi
 *
 * Failure:
 *   - sso_token yo'q → "Yaroqsiz so'rov" + login sahifasiga link
 *   - 401 backend → "Token muddati o'tgan" + qayta urinib ko'rish
 *   - 5xx → "Tarmoq xatosi" + qayta urinish
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
// Idempotent guard — Vue dev HMR'da onMounted ikki marta ishlamasin
let started = false

async function handleCallback() {
  if (started) return
  started = true

  const ssoToken = (route.query.sso_token as string) || ''
  if (!ssoToken) {
    status.value = 'error'
    errorMsg.value = t('auth.sso_missing_token')
    return
  }

  try {
    await auth.ssoHemis(ssoToken)
    status.value = 'success'
    // Kichik kechikish — foydalanuvchi muvaffaqiyat habarini ko'rsin
    setTimeout(() => {
      const redirect = (route.query.redirect as string) || '/app/dashboard'
      router.replace(redirect)
    }, 400)
  } catch {
    status.value = 'error'
    errorMsg.value = auth.error || t('auth.sso_invalid_token')
  }
}

onMounted(handleCallback)
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] max-w-md">
        HEMIS SSO
      </h2>
      <p class="opacity-60 max-w-sm leading-relaxed text-sm mt-6">
        {{ t('auth.sso_side_desc') }}
      </p>
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">HEMIS SSO · CALLBACK</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">
        {{ t('auth.sso_callback_title') }}
      </h1>
      <p class="text-muted-foreground text-sm">
        {{ t('auth.sso_callback_subtitle') }}
      </p>
    </div>

    <!-- Loading -->
    <div v-if="status === 'loading'" class="py-12 text-center">
      <div class="inline-block animate-spin rounded-full h-10 w-10 border-2 border-foreground border-t-transparent mb-4"></div>
      <p class="text-[13px] text-muted-foreground">{{ t('auth.sso_validating') }}</p>
    </div>

    <!-- Success -->
    <div v-else-if="status === 'success'" class="py-12 text-center">
      <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-success-500/15 text-success-600 mb-4">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 6 9 17l-5-5" />
        </svg>
      </div>
      <p class="text-[14px] font-medium text-foreground mb-1">
        {{ t('auth.sso_success_title') }}
      </p>
      <p class="text-[12px] text-muted-foreground">{{ t('auth.sso_success_subtitle') }}</p>
    </div>

    <!-- Error -->
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
