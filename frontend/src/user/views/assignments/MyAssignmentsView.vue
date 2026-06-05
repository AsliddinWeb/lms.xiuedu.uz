<script setup lang="ts">
/**
 * Wireframe 08 (Assignments) — talaba topshiriqlar ro'yxati.
 * - Page header: breadcrumb + h1 + subtitle + action buttons
 * - 4-stat grid (Jami, Bajarilmagan, Ko'rib chiqilmoqda, O'rtacha baho)
 * - Tabs: Hammasi / Bajarilmagan / Ko'rib chiqilmoqda / Baholangan
 * - Filter row: kurs/tur/muddat selectlar + total count
 * - Assignments cards (table emas, wireframe'da table ham bor — wireframe-faithful UX)
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import { assignmentsApi } from '@shared/api/assignments'
import { coursesApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { Assignment, Submission } from '@shared/types/assignments'
import type { Course } from '@shared/types/courses'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const items = ref<Assignment[]>([])
const courses = ref<Record<number, Course>>({})
const mySubmissions = ref<Record<number, Submission>>({})
const loading = ref(false)
const error = ref<string | null>(null)

type Tab = 'all' | 'pending' | 'in_review' | 'graded'
const activeTab = ref<Tab>('all')

const searchQ = ref('')
const courseFilter = ref<number | ''>('')
const typeFilter = ref<string>('')

const courseOptions = computed<{ value: string | number | null; label: string }[]>(() => [
  { value: '', label: t('my_assignments.all_courses') },
  ...Object.values(courses.value).map((c) => ({ value: c.id, label: c.title })),
])
const typeOptions = computed(() => [
  { value: '', label: t('my_assignments.all_types') },
  { value: 'essay', label: t('assignments.type_essay') },
  { value: 'file', label: t('assignments.type_file') },
])

function assignmentStatus(a: Assignment): 'pending' | 'in_review' | 'graded' | 'closed' {
  const sub = mySubmissions.value[a.id]
  if (sub?.status === 'graded') return 'graded'
  if (sub?.status === 'submitted' || sub?.status === 'grading') return 'in_review'
  if (a.closed_at && new Date(a.closed_at).getTime() < Date.now()) return 'closed'
  return 'pending'
}

const counts = computed(() => {
  let pending = 0
  let inReview = 0
  let graded = 0
  for (const a of items.value) {
    const s = assignmentStatus(a)
    if (s === 'pending') pending++
    else if (s === 'in_review') inReview++
    else if (s === 'graded') graded++
  }
  return { total: items.value.length, pending, inReview, graded }
})

const tabs = computed(() => [
  { id: 'all', label: t('my_assignments.tab_all'), count: counts.value.total },
  { id: 'pending', label: t('my_assignments.tab_pending'), count: counts.value.pending },
  { id: 'in_review', label: t('my_assignments.tab_in_review'), count: counts.value.inReview },
  { id: 'graded', label: t('my_assignments.tab_graded'), count: counts.value.graded },
])

const filteredItems = computed(() => {
  return items.value.filter((a) => {
    if (activeTab.value !== 'all' && assignmentStatus(a) !== activeTab.value) {
      return false
    }
    if (courseFilter.value && a.course_id !== courseFilter.value) return false
    if (typeFilter.value && a.type !== typeFilter.value) return false
    if (searchQ.value && !a.title.toLowerCase().includes(searchQ.value.toLowerCase())) {
      return false
    }
    return true
  })
})

const avgGrade = computed(() => {
  const graded = Object.values(mySubmissions.value).filter(
    (s) => s.status === 'graded' && s.final_score != null,
  )
  if (graded.length === 0) return '—'
  const total = graded.reduce((acc, s) => acc + Number(s.final_score), 0)
  return (total / graded.length).toFixed(1)
})

async function load() {
  if (!auth.user) return
  loading.value = true
  error.value = null
  try {
    const data = await assignmentsApi.list({
      mine: true,
      is_published: true,
      page_size: 100,
    })
    items.value = data.items

    // Course lookup
    const courseIds = Array.from(new Set(items.value.map((a) => a.course_id)))
    const missing = courseIds.filter((id) => !(id in courses.value))
    await Promise.all(
      missing.map(async (id) => {
        try {
          courses.value = { ...courses.value, [id]: await coursesApi.get(id) }
        } catch {
          /* ignore */
        }
      }),
    )

    // My submissions (eng so'nggi attempt)
    await Promise.all(
      items.value.map(async (a) => {
        try {
          const subs = await assignmentsApi.listMySubmissions(a.id)
          if (subs.length > 0) {
            mySubmissions.value = { ...mySubmissions.value, [a.id]: subs[0] }
          }
        } catch {
          /* ignore */
        }
      }),
    )
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

function open(a: Assignment) {
  router.push({ name: 'assignment-detail', params: { id: a.id } })
}

function daysUntil(s: string): number {
  return Math.ceil((new Date(s).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
}

function fmtDueDate(s: string): string {
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      day: '2-digit',
      month: 'short',
    }).format(new Date(s)).toUpperCase()
  } catch {
    return s.slice(0, 10)
  }
}

function statusBadge(a: Assignment): { variant: 'default' | 'success' | 'warning' | 'danger' | 'info'; label: string } {
  const status = assignmentStatus(a)
  if (status === 'graded') {
    const sub = mySubmissions.value[a.id]
    return {
      variant: 'success',
      label: sub?.final_score != null ? `${sub.final_score}` : t('my_assignments.status_graded'),
    }
  }
  if (status === 'in_review') return { variant: 'info', label: t('my_assignments.status_in_review') }
  if (status === 'closed') return { variant: 'warning', label: t('my_assignments.status_closed') }
  // pending — kalitiga qarab urgency
  const days = daysUntil(a.due_date)
  if (days <= 2) return { variant: 'danger', label: t('my_assignments.urgent_days', { n: days }) }
  if (days <= 7) return { variant: 'warning', label: t('my_assignments.due_days', { n: days }) }
  return { variant: 'default', label: t('my_assignments.due_days', { n: days }) }
}
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('assignments.title')]" />
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('assignments.title') }}</h1>
        <p class="page-subtitle">
          {{ t('my_assignments.subtitle', {
            pending: counts.pending,
            in_review: counts.inReview,
            graded: counts.graded,
          }) }}
        </p>
      </div>
    </div>
  </div>

  <!-- 4-STAT GRID -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
    <UiStatCard :label="t('my_assignments.stat_total')" :value="String(counts.total)" />
    <UiStatCard
      :label="t('my_assignments.stat_pending')"
      :value="String(counts.pending)"
      :tone="counts.pending > 0 ? 'danger' : 'default'"
      :hint="counts.pending > 0 ? t('my_assignments.hint_urgent') : ''"
    />
    <UiStatCard
      :label="t('my_assignments.stat_in_review')"
      :value="String(counts.inReview)"
    />
    <UiStatCard
      :label="t('my_assignments.stat_avg_grade')"
      :value="String(avgGrade)"
      :trend="avgGrade !== '—' && Number(avgGrade) >= 70 ? { direction: 'up', text: t('my_assignments.trend_good') } : undefined"
    />
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- TABS -->
  <UiTabs v-model="activeTab" :tabs="tabs" />

  <!-- FILTER ROW -->
  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="w-[180px]">
      <UiSelect v-model="courseFilter" :options="courseOptions" />
    </div>
    <div class="w-[160px]">
      <UiSelect v-model="typeFilter" :options="typeOptions" />
    </div>
    <div class="flex-1 min-w-[200px] max-w-[280px]">
      <UiInput v-model="searchQ" type="search" :placeholder="t('my_assignments.search_placeholder')" />
    </div>
    <span class="font-mono text-[11px] text-muted-foreground ml-auto uppercase tracking-wider">
      {{ t('my_assignments.results_count', { n: filteredItems.length }) }}
    </span>
  </div>

  <!-- ASSIGNMENT CARDS -->
  <div
    v-if="loading && items.length === 0"
    class="text-center py-12 text-muted-foreground"
  >
    {{ t('common.loading') }}
  </div>

  <UiEmptyState
    v-else-if="filteredItems.length === 0"
    variant="search"
    :title="t('my_assignments.no_results')"
    :description="t('my_assignments.no_results_hint')"
  >
    <template #action>
      <UiButton
        variant="outline"
        size="sm"
        @click="router.push({ name: 'my-learning' })"
      >
        {{ t('my_assignments.go_to_learning') }} →
      </UiButton>
    </template>
  </UiEmptyState>

  <div v-else class="space-y-3">
    <article
      v-for="a in filteredItems"
      :key="a.id"
      class="border border-border rounded-lg bg-card hover:border-border-strong transition-colors cursor-pointer p-4"
      @click="open(a)"
    >
      <div class="flex items-start gap-4">
        <!-- Course/type badge column -->
        <div class="flex flex-col gap-1.5 shrink-0 w-[120px]">
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {{ courses[a.course_id]?.title ?? `#${a.course_id}` }}
          </div>
          <UiBadge variant="default">{{ t(`assignments.type_${a.type}`) }}</UiBadge>
        </div>

        <!-- Main -->
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-[14px] mb-1">{{ a.title }}</h3>
          <p
            v-if="a.description"
            class="text-[12px] text-muted-foreground line-clamp-2 mb-2"
          >
            {{ a.description }}
          </p>
          <div class="flex items-center gap-3 font-mono text-[11px] text-muted-foreground">
            <span>📅 {{ fmtDueDate(a.due_date) }}</span>
            <span v-if="a.max_score">· {{ a.max_score }} {{ t('my_assignments.points') }}</span>
            <span v-if="a.max_attempts">· {{ a.max_attempts }} {{ t('my_assignments.attempts') }}</span>
          </div>
        </div>

        <!-- Status badge column -->
        <div class="shrink-0 flex flex-col items-end gap-2">
          <UiBadge :variant="statusBadge(a).variant" with-dot>
            {{ statusBadge(a).label }}
          </UiBadge>
          <UiButton variant="outline" size="sm" @click.stop="open(a)">
            {{ assignmentStatus(a) === 'graded'
              ? t('my_assignments.btn_view')
              : t('my_assignments.btn_open') }} →
          </UiButton>
        </div>
      </div>
    </article>
  </div>
</template>
