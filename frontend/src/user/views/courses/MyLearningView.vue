<script setup lang="ts">
/**
 * Wireframe 05 — talaba "Mening kurslarim" sahifasi (full versiya).
 *
 * Tarkibi:
 *   1. Page header — breadcrumb + h1 + subtitle
 *   2. 4 stat card — Jami / Davom etmoqda / Yakunlangan / Sertifikatlar
 *   3. Toolbar — search + tabs (Hammasi/Davom/Yakunlangan) + sort
 *   4. 3-col grid UiCourseCard'lar (filter + sort qo'llangan)
 *   5. Empty state har tab uchun
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCourseCard from '@shared/components/ui/UiCourseCard.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import { coursesApi, enrollmentsApi, progressApi } from '@shared/api/courses'
import { certificatesApi } from '@shared/api/certificates'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { useAuthStore } from '@shared/stores/auth'
import type { Course, CourseProgress } from '@shared/types/courses'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

interface Row {
  course: Course
  progress: CourseProgress
}

type TabId = 'all' | 'in_progress' | 'completed'
type SortKey = 'newest' | 'oldest' | 'progress_high' | 'progress_low' | 'title'

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const certByCourse = ref<Record<number, number>>({})

// Toolbar state
const activeTab = ref<TabId>('all')
const search = ref('')
const sortKey = ref<SortKey>('newest')

// ============================================================================
// Load
// ============================================================================

async function load() {
  if (!auth.user) return
  loading.value = true
  error.value = null
  try {
    const data = await coursesApi.list({
      enrolled_user_id: auth.user.id,
      page_size: 100,
    })
    const courses = data.items
    const progresses = await Promise.all(
      courses.map((c) => progressApi.myCourseProgress(c.id)),
    )
    rows.value = courses.map((course, i) => ({ course, progress: progresses[i] }))

    // Sertifikatlar (background)
    try {
      const certs = await certificatesApi.listMine()
      const map: Record<number, number> = {}
      for (const c of certs) {
        if (c.revoked_at === null) map[c.course_id] = c.id
      }
      certByCourse.value = map
    } catch {
      // ignore
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ============================================================================
// Computed: stats, tabs, filter, sort
// ============================================================================

const stats = computed(() => {
  const total = rows.value.length
  const completed = rows.value.filter(
    (r) => r.progress.completion_status === 'completed',
  ).length
  const inProgress = rows.value.filter(
    (r) => r.progress.completion_status !== 'completed',
  ).length
  const certificates = Object.keys(certByCourse.value).length
  return { total, completed, inProgress, certificates }
})

const tabs = computed(() => [
  { id: 'all', label: t('learning.tab_all'), count: stats.value.total },
  { id: 'in_progress', label: t('learning.tab_in_progress'), count: stats.value.inProgress },
  { id: 'completed', label: t('learning.tab_completed'), count: stats.value.completed },
])

const sortOptions = computed(() => [
  { value: 'newest', label: t('learning.sort_newest') },
  { value: 'oldest', label: t('learning.sort_oldest') },
  { value: 'progress_high', label: t('learning.sort_progress_high') },
  { value: 'progress_low', label: t('learning.sort_progress_low') },
  { value: 'title', label: t('learning.sort_title') },
])

const filteredRows = computed<Row[]>(() => {
  let list = rows.value

  // Tab filter
  if (activeTab.value === 'in_progress') {
    list = list.filter((r) => r.progress.completion_status !== 'completed')
  } else if (activeTab.value === 'completed') {
    list = list.filter((r) => r.progress.completion_status === 'completed')
  }

  // Search filter (title yoki teacher)
  const q = search.value.trim().toLowerCase()
  if (q) {
    list = list.filter((r) => {
      const title = (r.course.title ?? '').toLowerCase()
      return title.includes(q)
    })
  }

  // Sort
  const sorted = [...list]
  switch (sortKey.value) {
    case 'newest':
      sorted.sort(
        (a, b) =>
          new Date(b.course.created_at).getTime() -
          new Date(a.course.created_at).getTime(),
      )
      break
    case 'oldest':
      sorted.sort(
        (a, b) =>
          new Date(a.course.created_at).getTime() -
          new Date(b.course.created_at).getTime(),
      )
      break
    case 'progress_high':
      sorted.sort(
        (a, b) => Number(b.progress.percent ?? 0) - Number(a.progress.percent ?? 0),
      )
      break
    case 'progress_low':
      sorted.sort(
        (a, b) => Number(a.progress.percent ?? 0) - Number(b.progress.percent ?? 0),
      )
      break
    case 'title':
      sorted.sort((a, b) => a.course.title.localeCompare(b.course.title))
      break
  }
  return sorted
})

// ============================================================================
// Actions
// ============================================================================

async function handleUnenroll(c: Course) {
  const ok = await confirm({
    title: t('learning.unenroll_confirm'),
    description: c.title,
    variant: 'danger',
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await enrollmentsApi.selfUnenroll(c.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

function open(c: Course) {
  router.push({ name: 'course-detail', params: { id: c.id } })
}

function fmtDate(s: string): string {
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    }).format(new Date(s))
  } catch {
    return s.slice(0, 10)
  }
}

function courseCategory(c: Course): string {
  const parts: string[] = []
  if (c.type) parts.push(t(`courses.type_${c.type}`))
  if (c.level) parts.push(t(`courses.level_${c.level}`))
  return parts.join(' · ')
}
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('learning.title')]" />
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('learning.title') }}</h1>
        <p class="page-subtitle">{{ t('learning.subtitle') }}</p>
      </div>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- STAT GRID -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
    <UiStatCard
      :label="t('learning.stat_total')"
      :value="String(stats.total)"
    />
    <UiStatCard
      :label="t('learning.stat_in_progress')"
      :value="String(stats.inProgress)"
    />
    <UiStatCard
      :label="t('learning.stat_completed')"
      :value="String(stats.completed)"
      tone="success"
    />
    <UiStatCard
      :label="t('learning.stat_certificates')"
      :value="String(stats.certificates)"
    />
  </div>

  <!-- TABS -->
  <UiTabs
    v-model="activeTab"
    :tabs="tabs"
    class="mb-4"
  />

  <!-- TOOLBAR: search + sort -->
  <div class="flex flex-wrap items-center gap-3 mb-5">
    <div class="flex-1 min-w-[200px] max-w-[420px] relative">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <circle cx="6" cy="6" r="4" />
        <path d="m9 9 3 3" />
      </svg>
      <input
        v-model="search"
        :placeholder="t('learning.search_placeholder')"
        class="w-full bg-background border border-border rounded-md py-2 pl-9 pr-3 text-[13px] outline-none focus:border-foreground transition"
      />
    </div>
    <div class="flex items-center gap-2">
      <span class="text-[12px] font-mono uppercase tracking-wider text-muted-foreground">
        {{ t('learning.sort_label') }}
      </span>
      <UiSelect v-model="sortKey" :options="sortOptions" />
    </div>
  </div>

  <!-- LOADING -->
  <div v-if="loading && rows.length === 0" class="text-center py-16 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <!-- EMPTY STATE — initial (sahifa birinchi marta yoki hech kursga yozilmagan) -->
  <UiEmptyState
    v-else-if="rows.length === 0"
    :title="t('learning.no_courses')"
    :description="t('learning.no_courses_hint')"
  >
    <template #action>
      <UiButton variant="outline" size="sm" @click="router.push({ name: 'course-catalog' })">
        {{ t('learning.browse_catalog') }}
      </UiButton>
    </template>
  </UiEmptyState>

  <!-- EMPTY STATE — filter natijasi bo'sh (kurs bor, lekin tab/search bo'sh) -->
  <UiEmptyState
    v-else-if="filteredRows.length === 0"
    variant="search"
    :title="t('learning.no_filter_results')"
    :description="search ? t('learning.try_other_search') : t('learning.try_other_tab')"
  />

  <!-- 3-col grid -->
  <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
    <UiCourseCard
      v-for="{ course, progress } in filteredRows"
      :key="course.id"
      :title="course.title"
      :category="courseCategory(course)"
      :cover-url="course.cover_image_url"
      :progress="Number(progress.percent ?? 0)"
      :stats="[
        { icon: '📚', label: `${progress.completed_lessons}/${progress.total_required_lessons}` },
        course.estimated_hours ? { icon: '⏱', label: `${course.estimated_hours}h` } : null,
        { icon: '🌐', label: course.language },
      ].filter((s): s is { icon: string; label: string } => s !== null)"
      @click="open(course)"
    >
      <template #actions>
        <div class="flex items-center justify-between mt-3">
          <div class="flex items-center gap-1.5 flex-wrap">
            <UiBadge
              :variant="progress.completion_status === 'completed' ? 'success' : 'info'"
              with-dot
            >
              {{
                progress.completion_status === 'completed'
                  ? t('learning.completed')
                  : t('learning.in_progress')
              }}
            </UiBadge>
            <UiBadge
              v-if="certByCourse[course.id]"
              variant="default"
              class="cursor-pointer"
              @click.stop="$router.push({ name: 'my-certificates' })"
            >
              ★ {{ t('learning.cert_chip') }}
            </UiBadge>
          </div>

          <div class="flex items-center gap-1.5">
            <UiButton size="sm" @click.stop="open(course)">
              {{
                progress.completion_status === 'completed'
                  ? t('learning.review')
                  : t('learning.continue')
              }} →
            </UiButton>
            <button
              type="button"
              class="text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-700/15 rounded p-1.5"
              :title="t('learning.unenroll')"
              @click.stop="handleUnenroll(course)"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M3 3l8 8M11 3l-8 8" />
              </svg>
            </button>
          </div>
        </div>

        <div
          v-if="progress.completed_at"
          class="mt-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider"
        >
          ✓ {{ fmtDate(progress.completed_at) }}
        </div>
      </template>
    </UiCourseCard>
  </div>
</template>
