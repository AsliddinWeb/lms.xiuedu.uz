<script setup lang="ts">
/**
 * Phase 6g — Admin Reports (wireframe 18).
 *
 * 4 stat card + filter + per-exam table + CSV export.
 */

import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { reportsApi, type ExamReportSummary } from '@shared/api/reports'
import { extractErrorMessage } from '@shared/api/client'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'

const { t } = useI18n()

const courseId = ref<number | null>(null)
const examType = ref<string>('')
const dateFrom = ref<string>('')
const dateTo = ref<string>('')

const summary = ref<ExamReportSummary | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const totalFlagged = computed(() =>
  (summary.value?.items ?? []).reduce((acc, r) => acc + r.flagged_count, 0),
)

const typeOptions = computed(() => [
  { value: '', label: t('admin_reports.all_types') },
  { value: 'quiz', label: t('exams.type_quiz') },
  { value: 'midterm', label: t('exams.type_midterm') },
  { value: 'final', label: t('exams.type_final') },
  { value: 'dak', label: t('exams.type_dak') },
])

function fromLocalInput(v: string): string | null {
  if (!v) return null
  return new Date(v).toISOString()
}

async function load() {
  loading.value = true
  error.value = null
  try {
    summary.value = await reportsApi.examSummary({
      course_id: courseId.value,
      type: examType.value || null,
      date_from: fromLocalInput(dateFrom.value),
      date_to: fromLocalInput(dateTo.value),
    })
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function downloadCsv() {
  try {
    const blob = await reportsApi.downloadCsv({
      course_id: courseId.value,
      type: examType.value || null,
      date_from: fromLocalInput(dateFrom.value),
      date_to: fromLocalInput(dateTo.value),
    })
    downloadBlob(blob, timestampedFilename('imtihon_hisoboti'))
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin_reports.csv_error'))
  }
}

function reset() {
  courseId.value = null
  examType.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  load()
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb :items="['Admin', t('admin_reports.title')]" class="mb-6" />

  <div class="mb-6 flex items-start justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('admin_reports.title') }}</h1>
      <p class="page-subtitle">{{ t('admin_reports.subtitle') }}</p>
    </div>
    <UiButton @click="downloadCsv">⬇ {{ t('admin_reports.export_csv') }}</UiButton>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- Filter -->
  <UiCard class="mb-6">
    <div class="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
      <UiFormField :label="t('admin_reports.filter_course_id')">
        <UiInput v-model.number="courseId" type="number" min="1" placeholder="—" />
      </UiFormField>
      <UiFormField :label="t('admin_reports.filter_type')">
        <UiSelect v-model="examType" :options="typeOptions" />
      </UiFormField>
      <UiFormField :label="t('admin_reports.filter_date_from')">
        <UiInput v-model="dateFrom" type="datetime-local" />
      </UiFormField>
      <UiFormField :label="t('admin_reports.filter_date_to')">
        <UiInput v-model="dateTo" type="datetime-local" />
      </UiFormField>
      <div class="flex gap-2">
        <UiButton size="sm" :loading="loading" @click="load">
          {{ t('admin_reports.apply') }}
        </UiButton>
        <UiButton variant="ghost" size="sm" @click="reset">
          {{ t('admin_reports.reset') }}
        </UiButton>
      </div>
    </div>
  </UiCard>

  <!-- Stat cards -->
  <div v-if="summary" class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
    <UiStatCard
      :label="t('admin_reports.kpi_exams')"
      :value="String(summary.total_exams)"
    />
    <UiStatCard
      :label="t('admin_reports.kpi_attempts')"
      :value="String(summary.total_attempts)"
    />
    <UiStatCard
      :label="t('admin_reports.kpi_avg_score')"
      :value="`${summary.avg_percentage}%`"
    />
    <UiStatCard
      :label="t('admin_reports.kpi_pass_rate')"
      :value="`${summary.pass_rate}%`"
      tone="success"
    />
    <UiStatCard
      :label="t('admin_reports.kpi_flagged')"
      :value="String(totalFlagged)"
      :tone="totalFlagged > 0 ? 'warning' : 'default'"
    />
  </div>

  <!-- Table -->
  <UiCard v-if="summary" no-padding>
    <div v-if="summary.items.length === 0" class="p-12 text-center text-muted-foreground">
      {{ t('admin_reports.no_exams') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead class="bg-muted text-[11px] uppercase tracking-wider text-muted-foreground">
        <tr>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_reports.col_exam') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_reports.col_type') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_reports.col_course') }}</th>
          <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('admin_reports.col_attempts') }}</th>
          <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('admin_reports.col_avg') }}</th>
          <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('admin_reports.col_pass_rate') }}</th>
          <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('admin_reports.col_flagged') }}</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr
          v-for="row in summary.items"
          :key="row.exam_id"
          class="hover:bg-muted/30"
        >
          <td class="px-4 py-3">
            <div class="font-medium truncate max-w-[280px]">{{ row.exam_title }}</div>
            <div class="font-mono text-[11px] text-muted-foreground">
              #{{ row.exam_id }} · {{ t(`exams.status_${row.exam_status}`) }}
            </div>
          </td>
          <td class="px-4 py-3">
            <UiBadge variant="default">{{ t(`exams.type_${row.exam_type}`) }}</UiBadge>
          </td>
          <td class="px-4 py-3 text-muted-foreground truncate max-w-[200px]">
            {{ row.course_title }}
          </td>
          <td class="px-4 py-3 text-right font-mono">{{ row.attempts }}</td>
          <td class="px-4 py-3 text-right font-mono">{{ row.avg_percentage }}%</td>
          <td class="px-4 py-3 text-right font-mono">{{ row.pass_rate }}%</td>
          <td class="px-4 py-3 text-right font-mono">
            <span :class="row.flagged_count > 0 ? 'text-warning-600' : ''">
              {{ row.flagged_count }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </UiCard>
</template>
