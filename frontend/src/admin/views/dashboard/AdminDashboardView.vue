<script setup lang="ts">
/**
 * Admin Dashboard — platforma boshqaruv markazi.
 * KPI + grafiklar (/analytics/platform) + tezkor amallar + operatsion ro'yxatlar.
 */
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiChartBar from '@shared/components/ui/UiChartBar.vue'
import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import UiProgressRing from '@shared/components/ui/UiProgressRing.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { analyticsApi, coursesApi } from '@shared/api/courses'
import { liveSessionsApi } from '@shared/api/live'
import { hemisApi } from '@shared/api/hemis'
import { apiClient } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import { matches } from '@shared/composables/usePermissions'
import { formatDate, formatDateTime } from '@shared/utils/datetime'
import type { PlatformAnalytics, Course } from '@shared/types/courses'
import type { LiveSession } from '@shared/types/live'
import type { HemisSyncLogItem } from '@shared/api/hemis'

const { t, locale } = useI18n()
const auth = useAuthStore()

const data = ref<PlatformAnalytics | null>(null)
const upcoming = ref<LiveSession[]>([])
const recentCourses = ref<Course[]>([])
const recentSync = ref<HemisSyncLogItem[]>([])
const healthy = ref<boolean | null>(null)
const loading = ref(true)

const can = (perm: string) => auth.permissions.some((g) => matches(g, perm))

// Vaqtga qarab salomlashuv
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return t('admin_dashboard.greet_morning')
  if (h < 18) return t('admin_dashboard.greet_day')
  return t('admin_dashboard.greet_evening')
})
const today = computed(() => {
  try {
    return formatDate(new Date(), locale.value, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  } catch {
    return ''
  }
})

// --- Grafik ma'lumotlari ---
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

const roleRows = computed(() => {
  const rows = data.value?.users_by_role ?? []
  const max = Math.max(1, ...rows.map((r) => r.count))
  return rows.slice(0, 6).map((r) => ({ ...r, pct: Math.round((r.count / max) * 100) }))
})

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

// Kurs holati pipeline
const coursePipeline = computed(() => {
  const d = data.value
  if (!d) return []
  const total = Math.max(1, d.total_courses)
  return [
    { key: 'published', label: t('courses.status_published'), count: d.published_courses, tone: 'success' as const, to: '/courses?status=published' },
    { key: 'draft', label: t('courses.status_draft'), count: d.draft_courses, tone: 'warning' as const, to: '/courses?status=draft' },
    { key: 'archived', label: t('courses.status_archived'), count: d.archived_courses, tone: 'default' as const, to: '/courses?status=archived' },
  ].map((r) => ({ ...r, pct: Math.round((r.count / total) * 100) }))
})

// Tezkor amallar (ruxsatga qarab)
const quickActions = computed(() =>
  [
    { key: 'new_course', icon: 'courses', label: t('admin_dashboard.qa_new_course'), to: '/courses', perm: 'course.read' },
    { key: 'users', icon: 'users', label: t('admin_dashboard.qa_users'), to: '/users', perm: 'users.read' },
    { key: 'content', icon: 'content', label: t('admin_dashboard.qa_content'), to: '/content', perm: 'content.read' },
    { key: 'live', icon: 'live', label: t('admin_dashboard.qa_live'), to: '/live', perm: 'live.read' },
    { key: 'analytics', icon: 'analytics', label: t('admin_dashboard.qa_analytics'), to: '/analytics', perm: 'org.read' },
    { key: 'reports', icon: 'reports', label: t('admin_dashboard.qa_reports'), to: '/reports', perm: 'exam.create' },
    { key: 'hemis', icon: 'audit', label: t('admin_dashboard.qa_hemis'), to: '/hemis-sync', perm: 'exam.create' },
    { key: 'settings', icon: 'settings', label: t('admin_dashboard.qa_settings'), to: '/settings', perm: 'org.manage' },
  ].filter((a) => can(a.perm)),
)

function syncVariant(s: string): 'default' | 'success' | 'warning' | 'danger' {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'retrying' || s === 'pending') return 'warning'
  return 'default'
}
function courseStatusVariant(s: string): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

async function load() {
  loading.value = true
  const tasks = await Promise.allSettled([
    analyticsApi.platform(),
    liveSessionsApi.list({ status: 'scheduled', page_size: 20 }),
    coursesApi.list({ page: 1, page_size: 5 }),
    hemisApi.listSyncLog({ page_size: 5 }),
    apiClient.get('/health'),
  ])
  if (tasks[0].status === 'fulfilled') data.value = tasks[0].value
  if (tasks[1].status === 'fulfilled') {
    upcoming.value = [...tasks[1].value.items]
      .sort((a, b) => a.scheduled_start.localeCompare(b.scheduled_start))
      .slice(0, 5)
  }
  if (tasks[2].status === 'fulfilled') recentCourses.value = tasks[2].value.items
  if (tasks[3].status === 'fulfilled') recentSync.value = tasks[3].value.items
  healthy.value = tasks[4].status === 'fulfilled'
  loading.value = false
}
onMounted(load)
</script>

<template>
  <UiBreadcrumb :items="[t('admin_nav.overview'), t('admin_dashboard.title')]" class="mb-5" />

  <!-- Sarlavha -->
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">
        {{ greeting }}<span v-if="auth.user">, {{ auth.user.full_name }}</span>
      </h1>
      <p class="page-subtitle capitalize">{{ today }}</p>
    </div>
    <UiBadge :variant="healthy === false ? 'danger' : 'success'" with-dot>
      {{ healthy === false ? t('admin_dashboard.health_down') : t('admin_dashboard.health_ok') }}
    </UiBadge>
  </div>

  <div v-if="loading && !data" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <template v-else>
    <!-- KPI -->
    <div v-if="data" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
      <UiStatCard :label="t('admin_analytics.kpi_users')" :value="String(data.total_users)" :hint="t('admin_analytics.active_hint', { n: data.active_users })" />
      <UiStatCard :label="t('admin_analytics.kpi_courses')" :value="String(data.total_courses)" :hint="t('admin_analytics.published_hint', { n: data.published_courses })" />
      <UiStatCard :label="t('admin_analytics.kpi_students')" :value="String(data.total_students)" />
      <UiStatCard :label="t('admin_analytics.kpi_enrollments')" :value="String(data.total_enrollments)" />
      <UiStatCard :label="t('admin_analytics.kpi_completion')" :value="`${data.completion_rate}%`" tone="success" />
      <UiStatCard :label="t('admin_analytics.kpi_avg_grade')" :value="data.avg_grade !== null ? data.avg_grade.toFixed(1) : '—'" />
      <UiStatCard :label="t('admin_analytics.kpi_content')" :value="String(data.total_content)" />
      <UiStatCard :label="t('admin_analytics.kpi_live')" :value="String(data.total_live)" />
    </div>

    <!-- Tezkor amallar -->
    <div class="mb-6">
      <div class="mono-tag mb-2">{{ t('admin_dashboard.quick_actions') }}</div>
      <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        <RouterLink
          v-for="a in quickActions"
          :key="a.key"
          :to="a.to"
          class="flex flex-col items-center gap-2 rounded-lg border border-border bg-background px-3 py-4 text-center transition-colors hover:bg-muted hover:border-foreground/20 no-underline"
        >
          <span class="text-foreground"><UiNavIcon :name="a.icon" /></span>
          <span class="text-[12px] font-medium text-foreground leading-tight">{{ a.label }}</span>
        </RouterLink>
      </div>
    </div>

    <!-- Grafiklar 1-qator -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
      <UiCard :title="t('admin_analytics.enroll_trend_title')" class="lg:col-span-2">
        <UiChartBar v-if="enrollBars.length" :items="enrollBars" :height="180" />
        <div v-else class="h-[180px] grid place-items-center text-[12px] text-muted-foreground">
          {{ t('admin_dashboard.no_data') }}
        </div>
      </UiCard>

      <UiCard :title="t('admin_analytics.completion_title')">
        <div class="flex items-center gap-5">
          <UiProgressRing :percent="data?.completion_rate ?? 0" :size="92" :thickness="8" />
          <div class="flex-1 space-y-2">
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
    </div>

    <!-- Grafiklar 2-qator -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
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

      <UiCard :title="t('admin_analytics.grade_dist_title')">
        <div class="space-y-3">
          <div v-for="r in gradeRows" :key="r.key">
            <div class="flex justify-between text-[12px] mb-1">
              <span>{{ r.label }}</span>
              <span class="font-mono tabular-nums text-muted-foreground">{{ r.count }}</span>
            </div>
            <UiProgressBar :value="r.pct" size="sm" />
          </div>
        </div>
      </UiCard>

      <UiCard :title="t('admin_dashboard.pipeline_title')">
        <div class="space-y-3">
          <RouterLink
            v-for="r in coursePipeline"
            :key="r.key"
            :to="r.to"
            class="block no-underline group"
          >
            <div class="flex justify-between text-[12px] mb-1">
              <span class="flex items-center gap-1.5 text-foreground group-hover:underline">
                <span
                  class="w-1.5 h-1.5 rounded-full"
                  :class="{
                    'bg-success-500': r.tone === 'success',
                    'bg-warning-500': r.tone === 'warning',
                    'bg-muted-foreground': r.tone === 'default',
                  }"
                />
                {{ r.label }}
              </span>
              <span class="font-mono tabular-nums text-muted-foreground">{{ r.count }}</span>
            </div>
            <UiProgressBar :value="r.pct" size="sm" />
          </RouterLink>
        </div>
      </UiCard>
    </div>

    <!-- Operatsion ro'yxatlar -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Yaqin live darslar -->
      <UiCard :title="t('admin_dashboard.upcoming_live')">
        <template #actions>
          <RouterLink to="/live" class="text-[12px] text-muted-foreground hover:text-foreground no-underline">{{ t('admin_dashboard.view_all') }}</RouterLink>
        </template>
        <ul v-if="upcoming.length" class="divide-y divide-border -my-1">
          <li v-for="s in upcoming" :key="s.id" class="py-2.5">
            <div class="text-[13px] font-medium text-foreground truncate">{{ s.title }}</div>
            <div class="flex items-center justify-between mt-0.5">
              <span class="text-[11px] font-mono text-muted-foreground">{{ formatDateTime(s.scheduled_start, locale) }}</span>
              <span class="text-[11px] text-muted-foreground truncate ml-2">{{ s.host_full_name ?? `#${s.host_user_id}` }}</span>
            </div>
          </li>
        </ul>
        <div v-else class="py-6 text-center text-[12px] text-muted-foreground">{{ t('admin_dashboard.no_upcoming') }}</div>
      </UiCard>

      <!-- Oxirgi kurslar -->
      <UiCard :title="t('admin_dashboard.recent_courses')">
        <template #actions>
          <RouterLink to="/courses" class="text-[12px] text-muted-foreground hover:text-foreground no-underline">{{ t('admin_dashboard.view_all') }}</RouterLink>
        </template>
        <ul v-if="recentCourses.length" class="divide-y divide-border -my-1">
          <li v-for="c in recentCourses" :key="c.id" class="py-2.5 flex items-center justify-between gap-2">
            <RouterLink :to="`/courses/${c.id}`" class="text-[13px] font-medium text-foreground truncate hover:underline no-underline">{{ c.title }}</RouterLink>
            <UiBadge :variant="courseStatusVariant(c.status)" class="shrink-0">{{ t(`courses.status_${c.status}`) }}</UiBadge>
          </li>
        </ul>
        <div v-else class="py-6 text-center text-[12px] text-muted-foreground">{{ t('admin_dashboard.no_data') }}</div>
      </UiCard>

      <!-- Oxirgi HEMIS sinxronlash -->
      <UiCard :title="t('admin_dashboard.recent_hemis')">
        <template #actions>
          <RouterLink to="/hemis-sync" class="text-[12px] text-muted-foreground hover:text-foreground no-underline">{{ t('admin_dashboard.view_all') }}</RouterLink>
        </template>
        <ul v-if="recentSync.length" class="divide-y divide-border -my-1">
          <li v-for="s in recentSync" :key="s.id" class="py-2.5 flex items-center justify-between gap-2">
            <div class="min-w-0">
              <div class="text-[13px] text-foreground truncate">{{ s.sync_type }}</div>
              <div class="text-[11px] font-mono text-muted-foreground">{{ formatDateTime(s.created_at, locale) }}</div>
            </div>
            <UiBadge :variant="syncVariant(s.status)" with-dot class="shrink-0">{{ s.status }}</UiBadge>
          </li>
        </ul>
        <div v-else class="py-6 text-center text-[12px] text-muted-foreground">{{ t('admin_dashboard.no_data') }}</div>
      </UiCard>
    </div>
  </template>
</template>
