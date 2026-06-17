<script setup lang="ts">
/**
 * Admin — Platforma analitikasi (barcha kurslar/foydalanuvchilar bo'yicha aggregate).
 * Backend: GET /analytics/platform.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiChartBar from '@shared/components/ui/UiChartBar.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import UiProgressRing from '@shared/components/ui/UiProgressRing.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { analyticsApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import { formatDate } from '@shared/utils/datetime'
import type { PlatformAnalytics } from '@shared/types/courses'

const { t, locale } = useI18n()

const data = ref<PlatformAnalytics | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await analyticsApi.platform()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}
onMounted(load)

// Holat taqsimoti barlar
const statusRows = computed(() => {
  const c = data.value?.completion_breakdown
  if (!c) return []
  const rows = [
    { key: 'completed', label: t('students.completion_completed'), count: c.completed },
    { key: 'in_progress', label: t('students.completion_in_progress'), count: c.in_progress },
    { key: 'failed', label: t('students.completion_failed'), count: c.failed },
    { key: 'dropped', label: t('students.completion_dropped'), count: c.dropped },
  ]
  const max = Math.max(1, ...rows.map((r) => r.count))
  return rows.map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }))
})

// Baho taqsimoti barlar
const gradeRows = computed(() => {
  const g = data.value?.grade_distribution
  if (!g) return []
  const rows = [
    { key: 'excellent', label: t('statistics.grade_excellent'), count: g.excellent },
    { key: 'good', label: t('statistics.grade_good'), count: g.good },
    { key: 'satisfactory', label: t('statistics.grade_satisfactory'), count: g.satisfactory },
    { key: 'fail', label: t('statistics.grade_fail'), count: g.fail },
  ]
  const max = Math.max(1, ...rows.map((r) => r.count))
  return rows.map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }))
})

// Ro'yxat dinamikasi (oylar) -> UiChartBar
const enrollBars = computed(() => {
  const pts = data.value?.enrollments_over_time ?? []
  if (pts.length === 0) return []
  const max = Math.max(1, ...pts.map((p) => p.count))
  return pts.map((p) => {
    const [y, m] = p.month.split('-').map(Number)
    let label = p.month
    try {
      label = formatDate(new Date(y, m - 1, 1), locale.value, { month: 'short' })
    } catch {
      /* xom fallback */
    }
    return { label, value: Math.round((p.count / max) * 100), raw: p.count }
  })
})

// Rol bo'yicha foydalanuvchilar (eng kattaga nisbatan %)
const roleRows = computed(() => {
  const rows = data.value?.users_by_role ?? []
  const max = Math.max(1, ...rows.map((r) => r.count))
  return rows.map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }))
})

function statusVariant(s: string): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function exportCsv() {
  const d = data.value
  if (!d) return
  const esc = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`
  const lines: string[] = []
  lines.push([t('admin_analytics.col_course'), t('admin_analytics.col_status'), t('admin_analytics.col_enrollments')].map(esc).join(','))
  d.top_courses.forEach((c) => {
    lines.push([c.title, t(`courses.status_${c.status}`), c.enrollments].map(esc).join(','))
  })
  const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, timestampedFilename('platform-top-courses', 'csv'))
}
</script>

<template>
  <UiBreadcrumb :items="['Admin', t('admin_nav.overview'), t('admin_analytics.title')]" class="mb-4" />

  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <h1 class="page-title mb-1.5">{{ t('admin_analytics.title') }}</h1>
      <p class="page-subtitle">{{ t('admin_analytics.subtitle') }}</p>
    </div>
    <UiButton v-if="data" variant="outline" @click="exportCsv">
      {{ t('admin_analytics.export') }}
    </UiButton>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && !data" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <template v-else-if="data">
    <!-- KPI kartalar -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
      <UiStatCard
        :label="t('admin_analytics.kpi_users')"
        :value="String(data.total_users)"
        :hint="t('admin_analytics.active_hint', { n: data.active_users })"
      />
      <UiStatCard
        :label="t('admin_analytics.kpi_courses')"
        :value="String(data.total_courses)"
        :hint="t('admin_analytics.published_hint', { n: data.published_courses })"
      />
      <UiStatCard :label="t('admin_analytics.kpi_students')" :value="String(data.total_students)" />
      <UiStatCard :label="t('admin_analytics.kpi_enrollments')" :value="String(data.total_enrollments)" />
      <UiStatCard
        :label="t('admin_analytics.kpi_completion')"
        :value="`${data.completion_rate}%`"
        tone="success"
      />
      <UiStatCard
        :label="t('admin_analytics.kpi_avg_grade')"
        :value="data.avg_grade !== null ? data.avg_grade.toFixed(1) : '—'"
      />
      <UiStatCard :label="t('admin_analytics.kpi_content')" :value="String(data.total_content)" />
      <UiStatCard :label="t('admin_analytics.kpi_live')" :value="String(data.total_live)" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
      <!-- Tugatish darajasi + holat taqsimoti -->
      <UiCard :title="t('admin_analytics.completion_title')">
        <div class="flex items-center gap-5">
          <UiProgressRing :percent="data.completion_rate" :size="92" :thickness="8" />
          <div class="flex-1 space-y-2.5">
            <div v-for="r in statusRows" :key="r.key">
              <div class="flex justify-between text-[12px] mb-1">
                <span>{{ r.label }}</span>
                <span class="font-mono tabular-nums text-muted-foreground">{{ r.count }}</span>
              </div>
              <UiProgressBar :value="r.pct" size="sm" />
            </div>
          </div>
        </div>
      </UiCard>

      <!-- Baho taqsimoti -->
      <UiCard :title="t('admin_analytics.grade_dist_title')">
        <div class="space-y-3">
          <div v-for="r in gradeRows" :key="r.key">
            <div class="flex justify-between text-[12px] mb-1">
              <span>{{ r.label }}</span>
              <span class="font-mono tabular-nums text-muted-foreground">{{ r.count }}</span>
            </div>
            <UiProgressBar :value="r.pct" size="sm" />
          </div>
          <p v-if="data.avg_grade === null" class="text-[12px] text-muted-foreground italic pt-1">
            {{ t('statistics.no_grades') }}
          </p>
        </div>
      </UiCard>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
      <!-- Ro'yxat dinamikasi -->
      <UiCard :title="t('admin_analytics.enroll_trend_title')" class="lg:col-span-2">
        <UiChartBar v-if="enrollBars.length" :items="enrollBars" :height="180" />
        <div v-else class="h-[180px] grid place-items-center text-[12px] text-muted-foreground">
          {{ t('admin_analytics.no_data') }}
        </div>
      </UiCard>

      <!-- Imtihon pass-rate -->
      <UiCard :title="t('admin_analytics.exams_title')">
        <div class="flex items-center gap-4">
          <UiProgressRing
            :percent="data.exam_pass_rate ?? 0"
            :size="72"
            :thickness="7"
            :show-label="data.exam_pass_rate !== null"
          />
          <div>
            <div class="text-[13px] font-medium">{{ t('admin_analytics.exam_pass_rate') }}</div>
            <div class="text-[11px] text-muted-foreground font-mono">
              {{ t('admin_analytics.exam_attempts', { n: data.exam_attempts }) }}
            </div>
          </div>
        </div>
      </UiCard>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Rol bo'yicha foydalanuvchilar -->
      <UiCard :title="t('admin_analytics.roles_title')">
        <div class="space-y-2.5">
          <div v-for="r in roleRows" :key="r.code">
            <div class="flex justify-between text-[12px] mb-1">
              <span>{{ r.name }}</span>
              <span class="font-mono tabular-nums text-muted-foreground">{{ r.count }}</span>
            </div>
            <UiProgressBar :value="r.pct" size="sm" />
          </div>
        </div>
      </UiCard>

      <!-- Top kurslar -->
      <UiCard :title="t('admin_analytics.top_courses_title')" no-padding>
        <div class="overflow-x-auto">
          <table class="w-full text-[13px]">
            <thead>
              <tr class="bg-muted">
                <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                  {{ t('admin_analytics.col_course') }}
                </th>
                <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground w-[120px]">
                  {{ t('admin_analytics.col_enrollments') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in data.top_courses"
                :key="c.course_id"
                class="border-t border-border hover:bg-muted/30"
              >
                <td class="px-4 py-3">
                  <div class="font-medium truncate">{{ c.title }}</div>
                  <UiBadge :variant="statusVariant(c.status)" class="mt-1">
                    {{ t(`courses.status_${c.status}`) }}
                  </UiBadge>
                </td>
                <td class="px-4 py-3 font-mono tabular-nums">{{ c.enrollments }}</td>
              </tr>
              <tr v-if="data.top_courses.length === 0">
                <td colspan="2" class="px-4 py-6 text-center text-muted-foreground">
                  {{ t('admin_analytics.no_data') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </UiCard>
    </div>
  </template>
</template>
