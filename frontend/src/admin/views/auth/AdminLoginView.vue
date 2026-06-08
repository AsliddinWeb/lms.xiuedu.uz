<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { useAuthStore } from '@shared/stores/auth'

const ADMIN_ROLES = ['super_admin', 'dean', 'department_head', 'support']

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const errorMsg = ref<string | null>(null)

async function handleSubmit() {
  errorMsg.value = null
  try {
    const me = await auth.login({ email: email.value, password: password.value })
    if (!ADMIN_ROLES.some((r) => me.roles.includes(r))) {
      errorMsg.value = t('admin_auth.error_not_admin')
      await auth.logout()
      return
    }
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch {
    errorMsg.value = auth.error
  }
}
</script>

<template>
  <UiAuthLayout brand-title="Admin Console">
    <template #side>
      <div class="font-mono text-[11px] uppercase tracking-widest opacity-60 mb-3">
        {{ t('admin_auth.side_breadcrumb') }}
      </div>
      <h2 class="font-serif text-[40px] leading-[1.1] mb-6 max-w-md">
        {{ t('admin_auth.side_title') }} <em class="italic">{{ t('admin_auth.side_title_em') }}</em>.
      </h2>
      <p class="opacity-70 max-w-md leading-relaxed text-sm">
        {{ t('admin_auth.side_desc') }}
      </p>
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">{{ t('admin_auth.breadcrumb') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('admin_auth.title') }}</h1>
      <p class="text-muted-foreground text-sm">
        {{ t('admin_auth.subtitle') }}
        <a href="https://lms.xiuedu.uz" target="_blank" rel="noopener" class="text-foreground font-medium hover:underline">
          lms.xiuedu.uz
        </a>
        {{ t('admin_auth.subtitle_tail') }}
      </p>
    </div>

    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form @submit.prevent="handleSubmit">
      <UiFormField :label="t('auth.field_email')" required>
        <UiInput
          v-model="email"
          type="email"
          placeholder="admin@xiuedu.uz"
          autocomplete="email"
          required
        />
      </UiFormField>

      <UiFormField :label="t('auth.field_password')" required>
        <UiInput
          v-model="password"
          type="password"
          placeholder="••••••••••••"
          autocomplete="current-password"
          required
        />
      </UiFormField>

      <UiButton type="submit" :loading="auth.loading" full-width size="lg">
        {{ t('admin_auth.btn_login') }}
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7h8M7 3l4 4-4 4" />
        </svg>
      </UiButton>
    </form>
  </UiAuthLayout>
</template>
