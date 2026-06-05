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

  <!-- Kreativ karta grid — har kurs alohida sertifikat (Phase 27) -->
  <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    <UiCard
      v-for="c in items"
      :key="c.id"
      no-padding
      class="overflow-hidden flex flex-col"
    >
      <!-- Aksent header -->
      <div class="bg-[#1f3a5f] text-white px-4 py-3 flex items-start justify-between gap-2">
        <div class="min-w-0">
          <div class="font-mono text-[10px] uppercase tracking-widest text-[#e7d3a1]">
            {{ t('certificates.title') }}
          </div>
          <h3 class="text-[14px] font-semibold truncate mt-0.5">{{ c.course_title }}</h3>
        </div>
        <span class="text-xl shrink-0">🎓</span>
      </div>

      <!-- Tana -->
      <div class="p-4 flex-1 flex flex-col gap-3">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-full bg-[#e7d3a1] grid place-items-center shrink-0">
            <span class="text-lg">🏅</span>
          </div>
          <div class="min-w-0">
            <div class="text-[22px] font-semibold tabular-nums leading-none">
              {{ c.score_percentage ? `${c.score_percentage}%` : '—' }}
            </div>
            <div class="font-mono text-[11px] text-muted-foreground mt-1">
              {{ fmtDate(c.issued_at) }}
            </div>
          </div>
          <UiBadge
            :variant="c.revoked_at ? 'danger' : 'success'"
            class="ml-auto self-start"
          >
            {{ c.revoked_at ? t('certificates.status_revoked') : t('certificates.status_active') }}
          </UiBadge>
        </div>

        <div class="font-mono text-[11px] text-muted-foreground border-t border-border pt-2 truncate">
          {{ t('certificates.col_number') }}: {{ c.certificate_number }}
        </div>

        <div class="flex gap-2 mt-auto pt-1">
          <UiButton
            v-if="c.pdf_url && !c.revoked_at"
            size="sm"
            class="flex-1 justify-center"
            @click="openPdf(c)"
          >
            📥 {{ t('certificates.download_pdf') }}
          </UiButton>
          <UiButton
            variant="outline"
            size="sm"
            class="flex-1 justify-center"
            @click="openVerify(c)"
          >
            {{ t('certificates.open_verify') }}
          </UiButton>
        </div>
      </div>
    </UiCard>
  </div>
</template>
