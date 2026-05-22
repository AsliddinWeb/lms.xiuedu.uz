<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { authApi } from '@shared/api/auth'
import { extractErrorMessage } from '@shared/api/client'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const token = computed(() => (route.query.token as string) ?? '')

const password = ref('')
const passwordConfirm = ref('')
const submitting = ref(false)
const errorMsg = ref<string | null>(null)
const success = ref(false)

async function handleSubmit() {
  errorMsg.value = null
  if (!token.value) {
    errorMsg.value = t('auth.reset_no_token')
    return
  }
  if (password.value !== passwordConfirm.value) {
    errorMsg.value = t('auth.error_password_mismatch')
    return
  }
  submitting.value = true
  try {
    await authApi.resetPassword(token.value, password.value)
    success.value = true
    setTimeout(() => router.push({ name: 'login' }), 1500)
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] max-w-md">
        {{ t('auth.reset_side_title') }} <em class="italic">{{ t('auth.reset_side_title_em') }}</em>.
      </h2>
      <p class="opacity-60 max-w-sm leading-relaxed text-sm mt-6">
        {{ t('auth.reset_side_desc') }}
      </p>
    </template>

    <div class="mb-8">
      <div class="mono-tag mb-3">{{ t('auth.reset_breadcrumb') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('auth.reset_title') }}</h1>
      <p class="text-muted-foreground text-sm">{{ t('auth.reset_subtitle') }}</p>
    </div>

    <UiAlert v-if="!token" variant="warning" class="mb-4">
      {{ t('auth.reset_no_token') }}
    </UiAlert>

    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <UiAlert v-if="success" variant="success" class="mb-4">
      {{ t('auth.reset_success') }}
    </UiAlert>

    <form v-if="!success" @submit.prevent="handleSubmit">
      <UiFormField
        :label="t('auth.field_new_password')"
        :hint="t('auth.field_password_hint')"
        required
      >
        <UiInput
          v-model="password"
          type="password"
          placeholder="••••••••••••"
          autocomplete="new-password"
          required
        />
      </UiFormField>

      <UiFormField :label="t('auth.field_password_confirm')" required>
        <UiInput
          v-model="passwordConfirm"
          type="password"
          placeholder="••••••••••••"
          autocomplete="new-password"
          required
        />
      </UiFormField>

      <UiButton type="submit" :loading="submitting" :disabled="!token" full-width size="lg">
        {{ t('auth.btn_save_password') }}
      </UiButton>
    </form>

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
