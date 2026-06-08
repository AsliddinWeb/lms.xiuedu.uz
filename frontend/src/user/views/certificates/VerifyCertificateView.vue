<script setup lang="ts">
/**
 * Public sertifikat verifikatsiya — Phase 11d.
 *
 * `/verify/:code` marshrutida ochiladi (autentifikatsiyasiz). QR kod ushbu
 * URL'ga ko'rsatadi. Kod yo'q bo'lsa, user qo'lda kodni kiritishi mumkin.
 */

import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import {
  certificatesApi,
  type CertificateVerifyResponse,
} from '@shared/api/certificates'
import { formatDateTime } from '@shared/utils/datetime'

const { t, locale } = useI18n()
const route = useRoute()

const code = ref<string>((route.params.code as string) ?? '')
const result = ref<CertificateVerifyResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function check() {
  if (!code.value.trim()) return
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await certificatesApi.verify(code.value.trim())
  } catch (e) {
    error.value = (e as Error).message || 'Network error'
  } finally {
    loading.value = false
  }
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return formatDateTime(iso, locale.value)
}

onMounted(() => {
  if (code.value) void check()
})
</script>

<template>
  <div class="min-h-screen bg-background text-foreground flex flex-col items-center px-6 py-12">
    <div class="w-full max-w-2xl">
      <div class="text-center mb-8">
        <div class="mono-tag mb-2">{{ t('brand.platform') }}</div>
        <h1 class="text-[28px] font-semibold mb-2">
          {{ t('certificates.verify_title') }}
        </h1>
        <p class="text-[13px] text-muted-foreground">
          {{ t('certificates.verify_subtitle') }}
        </p>
      </div>

      <UiCard class="p-4 mb-4">
        <div class="flex items-end gap-2">
          <div class="flex-1">
            <UiInput
              v-model="code"
              :placeholder="t('certificates.verify_input_placeholder')"
              @keydown.enter="check"
            />
          </div>
          <UiButton :disabled="loading || !code.trim()" @click="check">
            {{ loading ? t('certificates.verify_loading') : t('certificates.verify_btn') }}
          </UiButton>
        </div>
      </UiCard>

      <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

      <div v-if="loading">
        <UiSkeleton :count="3" />
      </div>

      <!-- Sertifikat topilmadi -->
      <UiAlert
        v-else-if="result && !result.valid && !result.certificate_number"
        variant="danger"
      >
        {{ t('certificates.verify_invalid') }}
      </UiAlert>

      <!-- Bekor qilingan -->
      <div v-else-if="result && result.revoked_at">
        <UiAlert variant="danger" class="mb-3">
          {{ t('certificates.verify_revoked') }}
          <span v-if="result.revoke_reason">
            — {{ t('certificates.verify_revoke_reason', { reason: result.revoke_reason }) }}
          </span>
        </UiAlert>
        <UiCard class="p-5">
          <dl class="grid grid-cols-[140px_1fr] gap-y-2 text-[13px]">
            <dt class="text-muted-foreground">{{ t('certificates.col_number') }}</dt>
            <dd class="font-mono">{{ result.certificate_number }}</dd>
            <dt class="text-muted-foreground">{{ t('certificates.label_student') }}</dt>
            <dd>{{ result.student_name }}</dd>
            <dt class="text-muted-foreground">{{ t('certificates.label_course') }}</dt>
            <dd>{{ result.course_title }}</dd>
            <dt class="text-muted-foreground">{{ t('certificates.label_issued') }}</dt>
            <dd class="font-mono">{{ fmtDate(result.issued_at) }}</dd>
          </dl>
        </UiCard>
      </div>

      <!-- Haqiqiy sertifikat -->
      <div v-else-if="result && result.valid">
        <UiAlert variant="success" class="mb-3">
          ✓ {{ t('certificates.verify_valid') }}
        </UiAlert>
        <UiCard class="p-5">
          <dl class="grid grid-cols-[140px_1fr] gap-y-2 text-[13px]">
            <dt class="text-muted-foreground">{{ t('certificates.col_number') }}</dt>
            <dd class="font-mono">{{ result.certificate_number }}</dd>
            <dt class="text-muted-foreground">{{ t('certificates.label_student') }}</dt>
            <dd>{{ result.student_name }}</dd>
            <dt class="text-muted-foreground">{{ t('certificates.label_course') }}</dt>
            <dd>{{ result.course_title }}</dd>
            <dt class="text-muted-foreground">{{ t('certificates.label_issued') }}</dt>
            <dd class="font-mono">{{ fmtDate(result.issued_at) }}</dd>
            <template v-if="result.score_percentage">
              <dt class="text-muted-foreground">{{ t('certificates.col_score') }}</dt>
              <dd class="font-mono">{{ result.score_percentage }}%</dd>
            </template>
          </dl>
        </UiCard>
      </div>
    </div>
  </div>
</template>
