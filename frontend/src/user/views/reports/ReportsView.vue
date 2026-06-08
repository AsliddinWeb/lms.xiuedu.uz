<script setup lang="ts">
/**
 * Pedagog — Hisobotlar (Phase 35.3).
 *
 * Tayyor hisobotlarni CSV / PDF ko'rinishida yuklab olish. KPI'lar statistikadan
 * preview sifatida ko'rsatiladi; har bir karta alohida yuklab olish tugmasiga ega.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { analyticsApi, reportsApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import type { TeacherAnalytics } from '@shared/types/courses'

const { t } = useI18n()

const data = ref<TeacherAnalytics | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await analyticsApi.mine()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}
onMounted(load)

type ReportKey = 'courses' | 'students' | 'summary'

interface ReportDef {
  key: ReportKey
  icon: string
  format: 'CSV' | 'PDF'
  fetch: () => Promise<Blob>
  filename: string
  ext: 'csv' | 'pdf'
}

const reports: ReportDef[] = [
  {
    key: 'courses',
    icon: 'analytics',
    format: 'CSV',
    fetch: reportsApi.coursesCsv,
    filename: 'kurslar_hisoboti',
    ext: 'csv',
  },
  {
    key: 'students',
    icon: 'students',
    format: 'CSV',
    fetch: reportsApi.studentsCsv,
    filename: 'talabalar_hisoboti',
    ext: 'csv',
  },
  {
    key: 'summary',
    icon: 'certificates',
    format: 'PDF',
    fetch: reportsApi.summaryPdf,
    filename: 'pedagog_hisoboti',
    ext: 'pdf',
  },
]

const busy = ref<ReportKey | null>(null)
const downloadError = ref<string | null>(null)

async function download(r: ReportDef) {
  busy.value = r.key
  downloadError.value = null
  try {
    const blob = await r.fetch()
    downloadBlob(blob, timestampedFilename(r.filename, r.ext))
  } catch (e) {
    downloadError.value = extractErrorMessage(e, t('reports.download_error'))
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('nav.reports')]" class="mb-4" />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('nav.reports') }}</h1>
    <p class="page-subtitle">{{ t('reports.subtitle') }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>
  <UiAlert v-if="downloadError" variant="danger" class="mb-4">{{ downloadError }}</UiAlert>

  <!-- KPI preview -->
  <div v-if="data" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
    <UiStatCard :label="t('statistics.kpi_courses')" :value="String(data.total_courses)" />
    <UiStatCard :label="t('statistics.kpi_students')" :value="String(data.total_students)" />
    <UiStatCard
      :label="t('statistics.kpi_completion')"
      :value="`${data.completion_rate}%`"
      tone="success"
    />
    <UiStatCard
      :label="t('statistics.kpi_avg_grade')"
      :value="data.avg_grade !== null ? data.avg_grade.toFixed(1) : '—'"
    />
  </div>

  <!-- Hisobot kartalari -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <UiCard v-for="r in reports" :key="r.key" no-padding>
      <div class="p-5 flex flex-col h-full">
        <div class="flex items-start justify-between mb-3">
          <div
            class="size-11 rounded-xl grid place-items-center bg-primary/10 text-primary"
          >
            <UiNavIcon :name="r.icon" :size="22" />
          </div>
          <UiBadge :variant="r.format === 'PDF' ? 'danger' : 'info'">{{ r.format }}</UiBadge>
        </div>
        <h3 class="text-[15px] font-semibold mb-1">{{ t(`reports.${r.key}_title`) }}</h3>
        <p class="text-[13px] text-muted-foreground leading-relaxed flex-1 mb-4">
          {{ t(`reports.${r.key}_desc`) }}
        </p>
        <UiButton
          variant="outline"
          size="sm"
          :loading="busy === r.key"
          :disabled="busy !== null"
          class="w-full justify-center"
          @click="download(r)"
        >
          {{ t('reports.download') }}
        </UiButton>
      </div>
    </UiCard>
  </div>
</template>
