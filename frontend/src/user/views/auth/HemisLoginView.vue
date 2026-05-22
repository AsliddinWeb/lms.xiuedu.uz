<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// Phase 10g — 'student' (default) yoki 'tutor' (pedagog reCAPTCHA bilan)
const mode = ref<'student' | 'tutor'>('student')
const hemisLogin = ref('')
const hemisPassword = ref('')
const recaptcha = ref('')
const errorMsg = ref<string | null>(null)

async function handleSubmit() {
  errorMsg.value = null
  try {
    if (mode.value === 'student') {
      await auth.loginHemis(hemisLogin.value, hemisPassword.value)
    } else {
      // Mock mode: any non-empty captcha. Production: Google reCAPTCHA v3 SDK
      const captchaToken = recaptcha.value || 'mock-captcha-token'
      await auth.loginHemisTutor(
        hemisLogin.value,
        hemisPassword.value,
        captchaToken,
      )
    }
    const redirect = (route.query.redirect as string) || '/app/dashboard'
    router.push(redirect)
  } catch {
    errorMsg.value = auth.error
  }
}
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] max-w-md">
        {{ t('auth.hemis_side_title') }} <em class="italic">{{ t('auth.hemis_side_title_em') }}</em>.
      </h2>
      <p class="opacity-60 max-w-sm leading-relaxed text-sm mt-6">
        {{ t('auth.hemis_side_desc') }}
      </p>
    </template>

    <template #side-bottom>
      {{ t('auth.hemis_side_footer') }}
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">HEMIS SSO</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('auth.hemis_title') }}</h1>
      <p class="text-muted-foreground text-sm">{{ t('auth.hemis_subtitle') }}</p>
    </div>

    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <!-- Phase 10g — Role tabs: student / tutor -->
    <div class="flex border border-border rounded-md p-1 mb-5 bg-muted/40">
      <button
        type="button"
        class="flex-1 px-3 py-2 text-[13px] font-medium rounded transition-colors"
        :class="
          mode === 'student'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        "
        @click="mode = 'student'"
      >
        {{ t('auth.hemis_role_student') }}
      </button>
      <button
        type="button"
        class="flex-1 px-3 py-2 text-[13px] font-medium rounded transition-colors"
        :class="
          mode === 'tutor'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        "
        @click="mode = 'tutor'"
      >
        {{ t('auth.hemis_role_tutor') }}
      </button>
    </div>

    <form @submit.prevent="handleSubmit">
      <UiFormField
        :label="
          mode === 'tutor' ? t('auth.field_hemis_tutor_login') : t('auth.field_hemis_login')
        "
        :hint="
          mode === 'tutor' ? t('auth.field_hemis_tutor_login_hint') : t('auth.field_hemis_login_hint')
        "
        required
      >
        <UiInput
          v-model="hemisLogin"
          type="text"
          :placeholder="mode === 'tutor' ? 'pedagog_login' : '999211100073'"
          autocomplete="username"
          required
        />
      </UiFormField>

      <UiFormField :label="t('auth.field_hemis_password')" required>
        <UiInput
          v-model="hemisPassword"
          type="password"
          placeholder="••••••••••"
          autocomplete="current-password"
          required
        />
      </UiFormField>

      <!-- Phase 10g — reCAPTCHA placeholder (production'da Google reCAPTCHA v3 SDK) -->
      <UiFormField
        v-if="mode === 'tutor'"
        :label="t('auth.field_recaptcha')"
        :hint="t('auth.field_recaptcha_hint')"
      >
        <UiInput
          v-model="recaptcha"
          type="text"
          placeholder="mock-captcha-token"
          autocomplete="off"
        />
      </UiFormField>

      <UiButton type="submit" :loading="auth.loading" full-width size="lg">
        {{ mode === 'tutor' ? t('auth.btn_hemis_tutor_login') : t('auth.btn_hemis_login') }}
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7h8M7 3l4 4-4 4" />
        </svg>
      </UiButton>
    </form>

    <div
      class="mt-8 p-4 border border-border rounded-lg bg-muted/50 text-[12px] text-muted-foreground leading-relaxed"
    >
      {{ t('auth.hemis_info') }}
    </div>

    <div class="mt-8 pt-6 border-t border-border text-center">
      <RouterLink
        :to="{ name: 'login' }"
        class="text-[13px] text-foreground font-medium hover:underline inline-flex items-center gap-1.5"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 7H3M7 3L3 7l4 4" />
        </svg>
        {{ t('auth.back_to_email_login') }}
      </RouterLink>
    </div>
  </UiAuthLayout>
</template>
