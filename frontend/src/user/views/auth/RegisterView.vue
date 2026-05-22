<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiAuthLayout from '@shared/components/layout/UiAuthLayout.vue'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const fullName = ref('')
const email = ref('')
const phone = ref('')
const pinfl = ref('')
const password = ref('')
const passwordConfirm = ref('')
const acceptTerms = ref(false)

const errorMsg = ref<string | null>(null)
const success = ref(false)

// Parol kuchi indikatori (0..4)
const passwordStrength = computed(() => {
  const p = password.value
  let score = 0
  if (p.length >= 12) score++
  if (/[A-Z]/.test(p)) score++
  if (/[0-9]/.test(p)) score++
  if (/[^A-Za-z0-9]/.test(p)) score++
  return score
})

async function handleSubmit() {
  errorMsg.value = null
  if (password.value !== passwordConfirm.value) {
    errorMsg.value = t('auth.error_password_mismatch')
    return
  }
  if (!acceptTerms.value) {
    errorMsg.value = t('auth.error_terms_required')
    return
  }
  try {
    await auth.register({
      email: email.value,
      password: password.value,
      full_name: fullName.value,
      phone: phone.value || undefined,
    })
    await auth.login({ email: email.value, password: password.value })
    success.value = true
    setTimeout(() => router.push({ name: 'dashboard' }), 600)
  } catch {
    errorMsg.value = auth.error
  }
}
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <!-- LEFT SIDE: 3 numbered steps (wireframe 02) -->
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] mb-8 max-w-md">
        {{ t('auth.register_side_title') }}
        <em class="italic">{{ t('auth.register_side_title_em') }}</em>.
      </h2>

      <div class="flex flex-col gap-4 max-w-md">
        <div class="flex gap-3 items-start">
          <div class="w-7 h-7 border border-white/20 rounded-full grid place-items-center font-mono text-[11px] flex-shrink-0">01</div>
          <div>
            <div class="font-medium mb-1">{{ t('auth.step1_title') }}</div>
            <div class="text-[13px] opacity-60">{{ t('auth.step1_desc') }}</div>
          </div>
        </div>
        <div class="flex gap-3 items-start">
          <div class="w-7 h-7 border border-white/20 rounded-full grid place-items-center font-mono text-[11px] flex-shrink-0">02</div>
          <div>
            <div class="font-medium mb-1">{{ t('auth.step2_title') }}</div>
            <div class="text-[13px] opacity-60">{{ t('auth.step2_desc') }}</div>
          </div>
        </div>
        <div class="flex gap-3 items-start">
          <div class="w-7 h-7 border border-white/20 rounded-full grid place-items-center font-mono text-[11px] flex-shrink-0">03</div>
          <div>
            <div class="font-medium mb-1">{{ t('auth.step3_title') }}</div>
            <div class="text-[13px] opacity-60">{{ t('auth.step3_desc') }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- RIGHT SIDE: form -->
    <div class="mb-6">
      <div class="mono-tag mb-3">{{ t('auth.register_step_label') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('auth.register_title') }}</h1>
      <p class="text-muted-foreground text-sm">{{ t('auth.register_subtitle') }}</p>
    </div>

    <!-- Step progress (1/3 — Phase 1 da bizda 1 ta sahifa, lekin wireframe shu pattern) -->
    <div class="flex gap-1 mb-6">
      <div class="flex-1 h-[3px] bg-foreground rounded-sm"></div>
      <div class="flex-1 h-[3px] bg-border rounded-sm"></div>
      <div class="flex-1 h-[3px] bg-border rounded-sm"></div>
    </div>

    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <UiAlert v-if="success" variant="success" class="mb-4">
      {{ t('auth.register_success') }}
    </UiAlert>

    <form @submit.prevent="handleSubmit">
      <UiFormField :label="t('auth.field_full_name')" required>
        <UiInput
          v-model="fullName"
          placeholder="Karimov Bekzod Ahmedovich"
          autocomplete="name"
          required
        />
      </UiFormField>

      <UiFormField
        :label="t('auth.field_pinfl')"
        :hint="t('auth.field_pinfl_hint')"
      >
        <UiInput
          v-model="pinfl"
          placeholder="•••• •••• •••• ••"
          maxlength="14"
          inputmode="numeric"
        />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('auth.field_phone')">
          <UiInput
            v-model="phone"
            type="tel"
            placeholder="+998 90 123 45 67"
            autocomplete="tel"
          />
        </UiFormField>
        <UiFormField :label="t('auth.field_email')" required>
          <UiInput
            v-model="email"
            type="email"
            placeholder="email@example.uz"
            autocomplete="email"
            required
          />
        </UiFormField>
      </div>

      <UiFormField
        :label="t('auth.field_password')"
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
        <!-- Parol kuchi (wireframe 02 dagi parol indikator) -->
        <div v-if="password" class="flex gap-1 mt-2">
          <div
            v-for="i in 4"
            :key="i"
            class="flex-1 h-1 rounded-full transition-colors"
            :class="{
              'bg-danger-500': i <= passwordStrength && passwordStrength <= 1,
              'bg-warning-500': i <= passwordStrength && passwordStrength === 2,
              'bg-success-500': i <= passwordStrength && passwordStrength >= 3,
              'bg-muted': i > passwordStrength,
            }"
          ></div>
        </div>
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

      <label class="flex items-start gap-2 mb-6 cursor-pointer">
        <input
          v-model="acceptTerms"
          type="checkbox"
          class="w-3.5 h-3.5 mt-0.5 accent-foreground flex-shrink-0"
          required
        />
        <span class="text-[12px] text-muted-foreground leading-relaxed">
          <a href="#" class="text-foreground underline">{{ t('auth.terms_link') }}</a>
          {{ t('auth.terms_and') }}
          <a href="#" class="text-foreground underline">{{ t('auth.privacy_link') }}</a>
          {{ t('auth.terms_consent') }}
        </span>
      </label>

      <UiButton type="submit" :loading="auth.loading" full-width size="lg">
        {{ t('auth.btn_continue') }}
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7h8M7 3l4 4-4 4" />
        </svg>
      </UiButton>
    </form>

    <div class="mt-6 pt-6 border-t border-border text-center">
      <span class="text-[13px] text-muted-foreground">{{ t('auth.have_account') }}</span>
      <RouterLink
        :to="{ name: 'login' }"
        class="text-[13px] text-foreground font-medium ml-1 hover:underline"
      >
        {{ t('auth.to_login') }} →
      </RouterLink>
    </div>
  </UiAuthLayout>
</template>
