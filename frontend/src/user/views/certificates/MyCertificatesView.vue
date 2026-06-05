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

  <!-- Premium karta grid — har kurs alohida sertifikat (Phase 27) -->
  <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    <UiCard
      v-for="c in items"
      :key="c.id"
      no-padding
      class="overflow-hidden flex flex-col"
    >
      <!-- Premium header (navy gradient + gold accent) -->
      <div class="relative px-4 py-3.5 text-white bg-gradient-to-br from-[#16314f] via-[#1f3a5f] to-[#2e5180]">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="font-mono text-[10px] uppercase tracking-[0.18em] text-[#e7d3a1]">
              {{ t('certificates.title') }}
            </div>
            <h3 class="text-[14px] font-semibold truncate mt-1">{{ c.course_title }}</h3>
          </div>
          <span class="text-[#e7d3a1] shrink-0">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 10 12 5 2 10l10 5 10-5Z" />
              <path d="M6 12v5c0 1 2.7 2.5 6 2.5s6-1.5 6-2.5v-5" />
              <path d="M22 10v5" />
            </svg>
          </span>
        </div>
        <div class="absolute left-0 right-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-[#c19a3e] to-transparent"></div>
      </div>

      <!-- Tana -->
      <div class="p-4 flex-1 flex flex-col gap-3.5">
        <div class="flex items-center gap-3">
          <!-- Oltin medallion (award ikonka) -->
          <div class="w-12 h-12 rounded-full grid place-items-center shrink-0 text-[#1f3a5f] bg-gradient-to-br from-[#f3e6c4] to-[#d3a945] ring-1 ring-[#c19a3e]/50 shadow-sm">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="8" r="6" />
              <path d="M15.5 13.5 17 22l-5-3-5 3 1.5-8.5" />
            </svg>
          </div>
          <div class="min-w-0">
            <div class="text-[24px] font-bold tabular-nums leading-none text-foreground">
              {{ c.score_percentage ? `${c.score_percentage}%` : '—' }}
            </div>
            <div class="font-mono text-[11px] text-muted-foreground mt-1.5">
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

        <div class="font-mono text-[11px] text-muted-foreground border-t border-border pt-2.5 truncate">
          {{ t('certificates.col_number') }}: {{ c.certificate_number }}
        </div>

        <div class="flex gap-2 mt-auto pt-1">
          <UiButton
            v-if="c.pdf_url && !c.revoked_at"
            size="sm"
            class="flex-1 justify-center gap-1.5"
            @click="openPdf(c)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M7 10l5 5 5-5" />
              <path d="M12 15V3" />
            </svg>
            {{ t('certificates.download_pdf') }}
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
