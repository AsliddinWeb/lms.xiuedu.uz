<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { authApi } from '@shared/api/auth'
import { extractErrorMessage } from '@shared/api/client'

const { t } = useI18n()

const email = ref('')
const submitted = ref(false)
const submitting = ref(false)
const errorMsg = ref<string | null>(null)

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    await authApi.forgotPassword(email.value)
    submitted.value = true
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <!-- LEFT SIDE: short tagline (wireframe 03) -->
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] max-w-md">
        {{ t('auth.forgot_side_title') }} <em class="italic">{{ t('auth.forgot_side_title_em') }}</em>.
      </h2>
      <p class="opacity-60 max-w-sm leading-relaxed text-sm mt-6">
        {{ t('auth.forgot_side_desc') }}
      </p>
    </template>

    <template #side-bottom>
      {{ t('auth.forgot_side_footer') }}
    </template>

    <!-- RIGHT SIDE: form -->
    <div class="mb-8">
      <div class="mono-tag mb-3">{{ t('auth.forgot_breadcrumb') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('auth.forgot_title') }}</h1>
      <p class="text-muted-foreground text-sm">{{ t('auth.forgot_subtitle') }}</p>
    </div>

    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <UiAlert v-if="submitted" variant="success" class="mb-4">
      <strong>{{ t('auth.forgot_success_title') }}</strong>
      {{ t('auth.forgot_success_body') }}
      <span class="block mt-2 font-mono text-[11px] opacity-80">
        Dev: Mailhog — http://localhost:8215
      </span>
    </UiAlert>

    <form v-if="!submitted" @submit.prevent="handleSubmit">
      <UiFormField
        :label="t('auth.field_email')"
        :hint="t('auth.forgot_email_hint')"
        required
      >
        <UiInput
          v-model="email"
          type="email"
          placeholder="user@example.uz"
          autocomplete="email"
          required
        />
      </UiFormField>

      <UiButton type="submit" :loading="submitting" full-width size="lg" class="mb-3">
        {{ t('auth.btn_send_reset') }}
      </UiButton>

      <UiButton variant="outline" type="button" full-width size="lg" disabled>
        {{ t('auth.btn_sms_reset') }}
        <span class="font-mono text-[10px] text-muted-foreground ml-1">Ph.1e</span>
      </UiButton>
    </form>

    <!-- Wireframe info card (yordam izohlash) -->
    <div
      v-if="!submitted"
      class="mt-8 p-4 border border-border rounded-lg bg-muted/50"
    >
      <div class="flex gap-3 items-start">
        <div
          class="w-6 h-6 bg-foreground text-background rounded-full grid place-items-center flex-shrink-0 text-[10px]"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <circle cx="6" cy="3" r="1" />
            <rect x="5" y="5" width="2" height="5" rx="1" />
          </svg>
        </div>
        <div class="text-[12px] text-muted-foreground leading-relaxed">
          {{ t('auth.forgot_info') }}
          <a href="#" class="text-foreground underline">{{ t('auth.forgot_support_link') }}</a>
        </div>
      </div>
    </div>

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
