<script setup lang="ts">
/**
 * Kurslar katalogi (Phase 20.7) — talaba uchun kurs discovery sahifasi.
 *
 * Published kurslar grid'i: qidiruv + tur/daraja filtri + sort. Har kartada
 * yozilgan kurs "Ochish", self-enroll kurs "Yozilish", manual kurs "Ko'rish".
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCourseCard from '@shared/components/ui/UiCourseCard.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { coursesApi, enrollmentsApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import { useAuthStore } from '@shared/stores/auth'
import type { Course } from '@shared/types/courses'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const courses = ref<Course[]>([])
const enrolledIds = ref<Set<number>>(new Set())
const loading = ref(false)
const error = ref<string | null>(null)
const enrollingId = ref<number | null>(null)

// Toolbar state
const search = ref('')
const typeFilter = ref<string>('all')
const levelFilter = ref<string>('all')
const sortKey = ref<'newest' | 'oldest' | 'title'>('newest')

async function load() {
  loading.value = true
  error.value = null
  try {
    const published = await coursesApi.list({ status: 'published', page_size: 100 })
    courses.value = published.items

    if (auth.user) {
      try {
        const mine = await coursesApi.list({
          enrolled_user_id: auth.user.id,
          page_size: 100,
        })
        enrolledIds.value = new Set(mine.items.map((c) => c.id))
      } catch {
        enrolledIds.value = new Set()
      }
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

const typeOptions = computed(() => [
  { value: 'all', label: t('catalog.filter_all_types') },
  { value: 'academic', label: t('courses.type_academic') },
  { value: 'open', label: t('courses.type_open') },
  { value: 'micro', label: t('courses.type_micro') },
  { value: 'specialization', label: t('courses.type_specialization') },
])

const levelOptions = computed(() => [
  { value: 'all', label: t('catalog.filter_all_levels') },
  { value: 'beginner', label: t('courses.level_beginner') },
  { value: 'intermediate', label: t('courses.level_intermediate') },
  { value: 'advanced', label: t('courses.level_advanced') },
])

const sortOptions = computed(() => [
  { value: 'newest', label: t('catalog.sort_newest') },
  { value: 'oldest', label: t('catalog.sort_oldest') },
  { value: 'title', label: t('catalog.sort_title') },
])

const filtered = computed<Course[]>(() => {
  let list = courses.value

  if (typeFilter.value !== 'all') list = list.filter((c) => c.type === typeFilter.value)
  if (levelFilter.value !== 'all') list = list.filter((c) => c.level === levelFilter.value)

  const q = search.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        (c.description ?? '').toLowerCase().includes(q),
    )
  }

  const sorted = [...list]
  switch (sortKey.value) {
    case 'newest':
      sorted.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
      break
    case 'oldest':
      sorted.sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      )
      break
    case 'title':
      sorted.sort((a, b) => a.title.localeCompare(b.title))
      break
  }
  return sorted
})

function courseCategory(c: Course): string {
  const parts: string[] = []
  if (c.type) parts.push(t(`courses.type_${c.type}`))
  if (c.level) parts.push(t(`courses.level_${c.level}`))
  return parts.join(' · ')
}

function open(c: Course) {
  router.push({ name: 'course-detail', params: { id: c.id } })
}

async function handleEnroll(c: Course) {
  if (c.enrollment_type !== 'self') {
    open(c)
    return
  }
  enrollingId.value = c.id
  try {
    await enrollmentsApi.selfEnroll(c.id)
    enrolledIds.value = new Set([...enrolledIds.value, c.id])
    toast.success(t('catalog.enrolled_success'))
    open(c)
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.save_error'))
    error.value = msg
    toast.error(msg)
  } finally {
    enrollingId.value = null
  }
}
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('catalog.title')]" />
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('catalog.title') }}</h1>
        <p class="page-subtitle">{{ t('catalog.subtitle') }}</p>
      </div>
      <UiButton variant="outline" size="sm" @click="router.push({ name: 'my-learning' })">
        {{ t('catalog.go_my_learning') }} →
      </UiButton>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- TOOLBAR: search + filters + sort -->
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
        :placeholder="t('catalog.search_placeholder')"
        class="w-full bg-background border border-border rounded-md py-2 pl-9 pr-3 text-[13px] outline-none focus:border-foreground transition"
      />
    </div>
    <UiSelect v-model="typeFilter" :options="typeOptions" />
    <UiSelect v-model="levelFilter" :options="levelOptions" />
    <div class="flex items-center gap-2">
      <span class="text-[12px] font-mono uppercase tracking-wider text-muted-foreground">
        {{ t('catalog.sort_label') }}
      </span>
      <UiSelect v-model="sortKey" :options="sortOptions" />
    </div>
  </div>

  <!-- LOADING -->
  <div v-if="loading && courses.length === 0" class="text-center py-16 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <!-- EMPTY — umuman published kurs yo'q -->
  <UiEmptyState
    v-else-if="courses.length === 0"
    :title="t('catalog.no_courses')"
    :description="t('catalog.empty_hint')"
  />

  <!-- NO RESULTS — filter natijasi bo'sh -->
  <UiEmptyState
    v-else-if="filtered.length === 0"
    variant="search"
    :title="t('catalog.no_results')"
    :description="t('catalog.no_results_hint')"
  />

  <!-- 3-col grid -->
  <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
    <UiCourseCard
      v-for="c in filtered"
      :key="c.id"
      :title="c.title"
      :category="courseCategory(c)"
      :cover-url="c.cover_image_url"
      :stats="[
        c.duration_weeks ? { icon: '🗓', label: `${c.duration_weeks} ${t('catalog.weeks')}` } : null,
        c.estimated_hours ? { icon: '⏱', label: `${c.estimated_hours}h` } : null,
        { icon: '🌐', label: c.language },
      ].filter((s): s is { icon: string; label: string } => s !== null)"
      @click="open(c)"
    >
      <template #actions>
        <div class="flex items-center justify-between mt-3">
          <UiBadge v-if="enrolledIds.has(c.id)" variant="success" with-dot>
            {{ t('catalog.enrolled') }}
          </UiBadge>
          <UiBadge v-else-if="c.enrollment_type === 'self'" variant="info">
            {{ t('catalog.self_enroll_badge') }}
          </UiBadge>
          <span v-else class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
            {{ t('catalog.manual_enroll_badge') }}
          </span>

          <UiButton
            v-if="enrolledIds.has(c.id)"
            size="sm"
            @click.stop="open(c)"
          >
            {{ t('catalog.open_course') }} →
          </UiButton>
          <UiButton
            v-else-if="c.enrollment_type === 'self'"
            size="sm"
            :disabled="enrollingId === c.id"
            @click.stop="handleEnroll(c)"
          >
            {{ enrollingId === c.id ? t('catalog.enrolling') : t('catalog.enroll') }}
          </UiButton>
          <UiButton v-else size="sm" variant="outline" @click.stop="open(c)">
            {{ t('catalog.details') }} →
          </UiButton>
        </div>
      </template>
    </UiCourseCard>
  </div>
</template>
