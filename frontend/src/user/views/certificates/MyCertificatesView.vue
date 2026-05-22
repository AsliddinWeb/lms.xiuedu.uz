<script setup lang="ts">
/**
 * Mening sertifikatlarim — Phase 11d.
 */

import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import {
  certificatesApi,
  type CertificateMyItem,
} from '@shared/api/certificates'
import { extractErrorMessage } from '@shared/api/client'

const { t } = useI18n()

const items = ref<CertificateMyItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await certificatesApi.listMine()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString()
}

function openPdf(item: CertificateMyItem) {
  if (item.pdf_url) {
    window.open(item.pdf_url, '_blank', 'noopener')
  }
}

function openVerify(item: CertificateMyItem) {
  window.open(item.verification_url, '_blank', 'noopener')
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('certificates.title')]"
    class="mb-4"
  />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('certificates.title') }}</h1>
    <p class="page-subtitle">{{ t('certificates.subtitle') }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading">
    <UiSkeleton :count="3" />
  </div>

  <UiCard
    v-else-if="items.length === 0"
    class="py-12 text-center text-muted-foreground"
  >
    {{ t('certificates.empty') }}
  </UiCard>

  <UiCard v-else no-padding>
    <table class="w-full text-[13px]">
      <thead>
        <tr class="border-b border-border text-left text-[11px] font-mono uppercase text-muted-foreground">
          <th class="px-4 py-2.5">{{ t('certificates.col_number') }}</th>
          <th class="px-4 py-2.5">{{ t('certificates.col_course') }}</th>
          <th class="px-4 py-2.5">{{ t('certificates.col_issued') }}</th>
          <th class="px-4 py-2.5">{{ t('certificates.col_score') }}</th>
          <th class="px-4 py-2.5">{{ t('certificates.col_status') }}</th>
          <th class="px-4 py-2.5"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in items" :key="c.id" class="border-b border-border last:border-0">
          <td class="px-4 py-3 font-mono">{{ c.certificate_number }}</td>
          <td class="px-4 py-3">{{ c.course_title }}</td>
          <td class="px-4 py-3 font-mono">{{ fmtDate(c.issued_at) }}</td>
          <td class="px-4 py-3 font-mono">
            {{ c.score_percentage ? `${c.score_percentage}%` : '—' }}
          </td>
          <td class="px-4 py-3">
            <UiBadge :variant="c.revoked_at ? 'danger' : 'default'">
              {{ c.revoked_at ? t('certificates.status_revoked') : t('certificates.status_active') }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 text-right">
            <div class="flex gap-2 justify-end">
              <UiButton
                v-if="c.pdf_url && !c.revoked_at"
                variant="outline"
                size="sm"
                @click="openPdf(c)"
              >
                {{ t('certificates.download_pdf') }}
              </UiButton>
              <UiButton variant="outline" size="sm" @click="openVerify(c)">
                {{ t('certificates.open_verify') }}
              </UiButton>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </UiCard>
</template>
