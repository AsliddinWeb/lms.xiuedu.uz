<script setup lang="ts">
/**
 * Pedagog — Statistika (barcha kurslari bo'yicha aggregate analitika).
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import UiProgressRing from '@shared/components/ui/UiProgressRing.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import UiChartBar from '@shared/components/ui/UiChartBar.vue'
import { analyticsApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { intlLocale } from '@shared/i18n'
import type { TeacherAnalytics } from '@shared/types/courses'

const { t, locale } = useI18n()

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

// Baho taqsimoti barlar (count -> max'ga nisbatan %)
const gradeRows = computed(() => {
  const g = data.value?.grade_distribution
  if (!g) return []
  const rows = [
    { key: 'excellent', label: t('statistics.grade_excellent'), count: g.excellent, color: 'success' },
    { key: 'good', label: t('statistics.grade_good'), count: g.good, color: 'info' },
    { key: 'satisfactory', label: t('statistics.grade_satisfactory'), count: g.satisfactory, color: 'warning' },
    { key: 'fail', label: t('statistics.grade_fail'), count: g.fail, color: 'danger' },
  ]
  const max = Math.max(1, ...rows.map((r) => r.count))
  return rows.map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }))
})

// Holat taqsimoti
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

// Ro'yxat dinamikasi (oylar) -> UiChartBar (0-100 normallash)
const enrollBars = computed(() => {
  const pts = data.value?.enrollments_over_time ?? []
  if (pts.length === 0) return []
  const max = Math.max(1, ...pts.map((p) => p.count))
  return pts.map((p) => {
    const [y, m] = p.month.split('-').map(Number)
    let label = p.month
    try {
      label = new Intl.DateTimeFormat(intlLocale(locale.value), {
        month: 'short',
      }).format(new Date(y, m - 1, 1))
    } catch {
      /* xom fallback */
    }
    return { label, value: Math.round((p.count / max) * 100), raw: p.count }
  })
})
</script>

<template>
  <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('nav.statistics')]" class="mb-4" />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('nav.statistics') }}</h1>
    <p class="page-subtitle">{{ t('statistics.subtitle') }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && !data" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <template v-else-if="data">
    <!-- KPI kartalar -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      <UiStatCard
        :label="t('statistics.kpi_courses')"
        :value="String(data.total_courses)"
        :hint="t('statistics.published_hint', { n: data.published_courses })"
      />
      <UiStatCard :label="t('statistics.kpi_students')" :value="String(data.total_students)" />
      <UiStatCard :label="t('statistics.kpi_enrollments')" :value="String(data.total_enrollments)" />
      <UiStatCard
        :label="t('statistics.kpi_completion')"
        :value="`${data.completion_rate}%`"
        tone="success"
      />
      <UiStatCard
        :label="t('statistics.kpi_avg_grade')"
        :value="data.avg_grade !== null ? data.avg_grade.toFixed(1) : '—'"
      />
      <UiStatCard
        :label="t('statistics.kpi_pending')"
        :value="String(data.pending_grading)"
        :tone="data.pending_grading > 0 ? 'warning' : 'default'"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
      <!-- Tugatish darajasi + holat taqsimoti -->
      <UiCard :title="t('statistics.completion_title')">
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
      <UiCard :title="t('statistics.grade_dist_title')">
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

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Ro'yxat dinamikasi -->
      <UiCard :title="t('statistics.enroll_trend_title')" class="lg:col-span-2">
        <UiChartBar v-if="enrollBars.length" :items="enrollBars" :height="180" />
        <div v-else class="h-[180px] grid place-items-center text-[12px] text-muted-foreground">
          {{ t('statistics.no_data') }}
        </div>
      </UiCard>

      <!-- Imtihon + live -->
      <UiCard :title="t('statistics.other_title')">
        <div class="space-y-4">
          <div class="flex items-center gap-4">
            <UiProgressRing
              :percent="data.exam_pass_rate ?? 0"
              :size="64"
              :thickness="6"
              :show-label="data.exam_pass_rate !== null"
            />
            <div>
              <div class="text-[13px] font-medium">{{ t('statistics.exam_pass_rate') }}</div>
              <div class="text-[11px] text-muted-foreground font-mono">
                {{ t('statistics.exam_attempts', { n: data.exam_attempts }) }}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-4 border-t border-border pt-4">
            <div class="text-[28px] font-bold tabular-nums leading-none w-16 text-center">
              {{ data.live_sessions_count }}
            </div>
            <div class="text-[13px]">{{ t('statistics.live_sessions') }}</div>
          </div>
        </div>
      </UiCard>
    </div>
  </template>
</template>
