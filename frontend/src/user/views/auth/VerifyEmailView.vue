<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { authApi } from '@shared/api/auth'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const status = ref<'pending' | 'ok' | 'error' | 'no_token'>('pending')
const errorMsg = ref<string | null>(null)

onMounted(async () => {
  const token = route.query.token as string | undefined
  if (!token) {
    status.value = 'no_token'
    return
  }
  try {
    await authApi.verifyEmail(token)
    status.value = 'ok'
    if (auth.isAuthenticated) await auth.fetchMe()
  } catch (e) {
    status.value = 'error'
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  }
})

function goNext() {
  if (auth.isAuthenticated) router.push({ name: 'dashboard' })
  else router.push({ name: 'login' })
}
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] max-w-md">
        {{ t('auth.verify_side_title') }} <em class="italic">{{ t('auth.verify_side_title_em') }}</em>.
      </h2>
      <p class="opacity-60 max-w-sm leading-relaxed text-sm mt-6">
        {{ t('auth.verify_side_desc') }}
      </p>
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">{{ t('auth.verify_breadcrumb') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('auth.verify_title') }}</h1>
    </div>

    <UiAlert v-if="status === 'pending'" variant="info" class="mb-4">
      {{ t('auth.verify_pending') }}
    </UiAlert>

    <UiAlert v-else-if="status === 'no_token'" variant="warning" class="mb-4">
      {{ t('auth.verify_no_token') }}
    </UiAlert>

    <UiAlert v-else-if="status === 'ok'" variant="success" class="mb-4">
      <strong>{{ t('auth.verify_ok_title') }}</strong>
      {{ t('auth.verify_ok_body') }}
    </UiAlert>

    <UiAlert v-else variant="danger" class="mb-4">
      {{ errorMsg || t('auth.verify_error') }}
    </UiAlert>

    <UiButton
      v-if="status === 'ok' || status === 'error'"
      full-width
      size="lg"
      @click="goNext"
    >
      {{ auth.isAuthenticated ? t('auth.btn_goto_dashboard') : t('auth.btn_goto_login') }} →
    </UiButton>

    <div class="mt-8 pt-6 border-t border-border text-center">
      <RouterLink
        :to="{ name: 'login' }"
        class="text-[13px] text-foreground font-medium hover:underline inline-flex items-center gap-1.5"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 7H3M7 3L3 7l4 4" />
        </svg>
        {{ t('auth.back_to_login') }}
      </RouterLink>
    </div>
  </UiAuthLayout>
</template>
