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

const ADMIN_ROLES = ['super_admin', 'otm_admin', 'dean', 'department_head', 'support']

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
      <p class="opacity-70 max-w-sm leading-relaxed text-sm">
        {{ t('admin_auth.side_desc') }}
      </p>

      <div class="grid grid-cols-3 gap-6 pt-8 mt-12 border-t border-white/10 max-w-md">
        <div>
          <div class="font-mono text-[11px] opacity-60 uppercase tracking-wider mb-1">
            {{ t('admin_auth.feature_security') }}
          </div>
          <div class="text-sm font-semibold">2FA + IP</div>
        </div>
        <div>
          <div class="font-mono text-[11px] opacity-60 uppercase tracking-wider mb-1">
            {{ t('admin_auth.feature_audit') }}
          </div>
          <div class="text-sm font-semibold">{{ t('admin_auth.feature_audit_val') }}</div>
        </div>
        <div>
          <div class="font-mono text-[11px] opacity-60 uppercase tracking-wider mb-1">
            SLA
          </div>
          <div class="text-sm font-semibold">99.9%</div>
        </div>
      </div>
    </template>

    <template #side-bottom>
      {{ t('admin_auth.side_footer') }}
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">{{ t('admin_auth.breadcrumb') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('admin_auth.title') }}</h1>
      <p class="text-muted-foreground text-sm">
        {{ t('admin_auth.subtitle') }}
        <a href="http://localhost:8201" class="text-foreground font-medium hover:underline">
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

    <div
      class="mt-8 font-mono text-[10px] text-muted-foreground text-center leading-relaxed uppercase tracking-wider"
    >
      {{ t('admin_auth.audit_note') }}
    </div>
  </UiAuthLayout>
</template>
