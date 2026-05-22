<script setup lang="ts">
import axios from 'axios'
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

const email = ref('')
const password = ref('')
const totpCode = ref('')
const remember = ref(false)

const requires2FA = ref(false)
const errorMsg = ref<string | null>(null)

async function handleSubmit() {
  errorMsg.value = null
  try {
    await auth.login({
      email: email.value,
      password: password.value,
      totp_code: totpCode.value || undefined,
    })
    const redirect = (route.query.redirect as string) || '/app/dashboard'
    router.push(redirect)
  } catch (err) {
    if (axios.isAxiosError(err)) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string' && /2FA/i.test(detail)) {
        requires2FA.value = true
        errorMsg.value = null
        return
      }
    }
    errorMsg.value = auth.error
  }
}
</script>

<template>
  <UiAuthLayout :brand-title="t('brand.platform')">
    <!-- LEFT SIDE: tagline + stats grid (wireframe 01) -->
    <template #side>
      <h2 class="font-serif text-[40px] leading-[1.1] mb-6 max-w-md" v-html="t('brand.tagline_serif')"></h2>
      <p class="opacity-70 max-w-sm leading-relaxed text-sm">
        {{ t('brand.description') }}
      </p>

      <div class="grid grid-cols-3 gap-6 pt-8 mt-12 border-t border-white/10 max-w-md">
        <div>
          <div class="font-mono text-2xl font-semibold tabular-nums">120K+</div>
          <div class="text-[11px] opacity-60 uppercase tracking-wider mt-1">
            {{ t('brand.stat_students') }}
          </div>
        </div>
        <div>
          <div class="font-mono text-2xl font-semibold tabular-nums">85+</div>
          <div class="text-[11px] opacity-60 uppercase tracking-wider mt-1">
            {{ t('brand.stat_otm') }}
          </div>
        </div>
        <div>
          <div class="font-mono text-2xl font-semibold tabular-nums">99.9%</div>
          <div class="text-[11px] opacity-60 uppercase tracking-wider mt-1">
            {{ t('brand.stat_uptime') }}
          </div>
        </div>
      </div>
    </template>

    <!-- RIGHT SIDE: form -->
    <div class="mb-8">
      <div class="mono-tag mb-3">{{ t('auth.login_title') }}</div>
      <h1 class="text-[28px] font-semibold tracking-tight mb-2">{{ t('auth.login_welcome') }}</h1>
      <p class="text-muted-foreground text-sm">{{ t('auth.login_subtitle') }}</p>
    </div>

    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <!-- Phase 10d — HEMIS primary login (recommended for students) -->
    <RouterLink :to="{ name: 'hemis-login' }" class="block mb-2.5">
      <UiButton variant="primary" full-width type="button" size="lg">
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="4" width="16" height="12" rx="2" />
          <path d="M2 8h16" />
        </svg>
        {{ t('auth.with_hemis') }}
      </UiButton>
    </RouterLink>
    <p class="text-[12px] text-muted-foreground mb-4 text-center">
      {{ t('auth.hemis_recommended') }}
    </p>

    <UiButton variant="outline" full-width class="mb-2.5" disabled>
      <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
        <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="2" fill="none" />
        <path d="M6 10h8M10 6v8" stroke="currentColor" stroke-width="2" />
      </svg>
      {{ t('auth.with_oneid') }}
      <span class="font-mono text-[10px] text-muted-foreground ml-1">Ph.1e</span>
    </UiButton>

    <!-- Divider — admin/staff email login -->
    <div class="flex items-center gap-3 my-6 text-muted-foreground">
      <div class="flex-1 h-px bg-border"></div>
      <span class="font-mono text-[11px] uppercase tracking-wider">{{ t('auth.or_email_admin') }}</span>
      <div class="flex-1 h-px bg-border"></div>
    </div>

    <form @submit.prevent="handleSubmit">
      <UiFormField :label="t('auth.field_email_or_pinfl')" required>
        <UiInput
          v-model="email"
          type="email"
          placeholder="user@example.uz"
          autocomplete="email"
          required
        />
      </UiFormField>

      <UiFormField
        :label="t('auth.field_password')"
        required
        :right-link="{ label: t('auth.forgot_link'), to: '/forgot-password' }"
      >
        <UiInput
          v-model="password"
          type="password"
          placeholder="••••••••••••"
          autocomplete="current-password"
          required
        />
      </UiFormField>

      <UiFormField
        v-if="requires2FA"
        label="2FA"
        hint="Authenticator (6 raqam) yoki backup code (9 belgi)"
        required
      >
        <UiInput
          v-model="totpCode"
          type="text"
          placeholder="123456"
          autocomplete="one-time-code"
          required
        />
      </UiFormField>

      <label class="flex items-center gap-2 mb-6 cursor-pointer">
        <input v-model="remember" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px] text-muted-foreground">{{ t('auth.remember_me') }}</span>
      </label>

      <UiButton type="submit" :loading="auth.loading" full-width size="lg">
        {{ t('auth.login_btn') }}
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7h8M7 3l4 4-4 4" />
        </svg>
      </UiButton>
    </form>

    <div class="mt-8 pt-6 border-t border-border text-center">
      <span class="text-[13px] text-muted-foreground">{{ t('auth.no_account') }}</span>
      <RouterLink
        :to="{ name: 'register' }"
        class="text-[13px] text-foreground font-medium ml-1 hover:underline"
      >
        {{ t('auth.to_register') }} →
      </RouterLink>
    </div>

    <div
      class="mt-8 font-mono text-[10px] text-muted-foreground text-center leading-relaxed uppercase tracking-wider"
    >
      {{ t('brand.footer_legal') }}
    </div>
  </UiAuthLayout>
</template>
