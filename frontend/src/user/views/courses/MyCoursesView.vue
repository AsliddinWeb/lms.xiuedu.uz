<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { coursesApi } from '@shared/api/courses'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { Course, CourseStatus } from '@shared/types/courses'

import CourseDrawer from '@user/components/courses/CourseDrawer.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const items = ref<Course[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQ = ref('')
const statusFilter = ref<CourseStatus | 'all'>('all')

const drawerOpen = ref(false)
const editing = ref<Course | null>(null)

const filtered = computed(() => {
  let list = items.value
  if (statusFilter.value !== 'all') list = list.filter((c) => c.status === statusFilter.value)
  return list
})

async function load() {
  if (!auth.user) return
  loading.value = true
  error.value = null
  try {
    const data = await coursesApi.list({
      primary_author_id: auth.user.id,
      q: searchQ.value || undefined,
      page_size: 100,
    })
    items.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  // Sidebar'dan "Kurs konstruktori" bosilganda ?new=1 query bilan kelsa,
  // avtomatik "+ Yangi kurs" drawer'ini ochamiz va URL'ni tozalaymiz.
  if (route.query.new === '1') {
    openCreate()
    router.replace({ query: {} })
  }
})

// Sidebar'dan ?new=1 bilan qayta kirilsa ham drawer'ni ochish
watch(
  () => route.query.new,
  (val) => {
    if (val === '1') {
      openCreate()
      router.replace({ query: {} })
    }
  },
)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQ, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}

function openEdit(c: Course) {
  editing.value = c
  drawerOpen.value = true
}

function openBuilder(c: Course) {
  router.push({ name: 'course-builder', params: { id: c.id } })
}

async function handleDelete(c: Course) {
  const ok = await confirm({
    title: t('courses.delete_confirm'),
    description: c.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await coursesApi.remove(c.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

async function togglePublish(c: Course) {
  try {
    if (c.status === 'published') await coursesApi.unpublish(c.id)
    else await coursesApi.publish(c.id)
    await load()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

function statusVariant(s: CourseStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function typeLabel(c: Course): string {
  return t(`courses.type_${c.type}`)
}

function levelLabel(c: Course): string | null {
  return c.level ? t(`courses.level_${c.level}`) : null
}
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('courses.title')]"
    class="mb-6"
  />

  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('courses.title') }}</h1>
      <p class="page-subtitle">{{ t('courses.subtitle') }}</p>
    </div>
    <UiButton v-if="auth.hasPermission('course.create')" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('courses.new') }}
    </UiButton>
  </div>

  <!-- Filter row (wireframe 12 pattern) -->
  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="flex items-center gap-1">
      <button
        v-for="opt in (['all', 'draft', 'published', 'archived'] as const)"
        :key="opt"
        type="button"
        class="px-3 py-1.5 rounded-md text-[12px] font-medium border transition-colors"
        :class="
          statusFilter === opt
            ? 'bg-foreground text-background border-foreground'
            : 'bg-background text-foreground border-border-strong hover:bg-muted'
        "
        @click="statusFilter = opt"
      >
        {{ t(opt === 'all' ? 'courses.filter_all' : `courses.filter_${opt}`) }}
      </button>
    </div>
    <div class="w-px h-7 bg-border mx-1" aria-hidden="true"></div>
    <div class="flex-1 min-w-[200px] max-w-[320px]">
      <UiInput
        v-model="searchQ"
        type="search"
        :placeholder="t('courses.search_placeholder')"
      />
    </div>
    <span class="font-mono text-[11px] text-muted-foreground ml-auto uppercase tracking-wider">
      {{ filtered.length }} {{ t('my_courses.courses_count') }}
    </span>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && items.length === 0" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <div
    v-else-if="filtered.length === 0"
    class="text-center py-16 border border-dashed border-border rounded-lg text-muted-foreground"
  >
    {{ t('courses.no_courses') }}
  </div>

  <!-- Wireframe 12 table -->
  <UiCard v-else no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('my_courses.col_course') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('my_courses.col_type') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('my_courses.col_duration') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('my_courses.col_level') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('my_courses.col_status') }}
            </th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in filtered"
            :key="c.id"
            class="border-t border-border hover:bg-muted/30"
          >
            <td class="px-4 py-3">
              <div class="font-medium">{{ c.title }}</div>
              <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
                /{{ c.slug }} · {{ c.language.toUpperCase() }}
              </div>
            </td>
            <td class="px-4 py-3">
              <UiBadge variant="default">{{ typeLabel(c) }}</UiBadge>
            </td>
            <td class="px-4 py-3 font-mono text-[12px]">
              <template v-if="c.duration_weeks">
                {{ c.duration_weeks }}{{ t('course_detail.weeks').charAt(0) }}
              </template>
              <template v-else>—</template>
              <template v-if="c.estimated_hours">
                · {{ c.estimated_hours }}{{ t('course_detail.hours').charAt(0) }}
              </template>
            </td>
            <td class="px-4 py-3 font-mono text-[12px]">
              {{ levelLabel(c) ?? '—' }}
            </td>
            <td class="px-4 py-3">
              <UiBadge :variant="statusVariant(c.status)" with-dot>
                {{ t(`courses.status_${c.status}`) }}
              </UiBadge>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end gap-1.5">
                <UiButton variant="outline" size="sm" @click="openBuilder(c)">
                  {{ t('courses.open_builder') }}
                </UiButton>
                <UiButton
                  v-if="c.status !== 'published'"
                  variant="ghost"
                  size="sm"
                  @click="openEdit(c)"
                >
                  {{ t('courses.edit') }}
                </UiButton>
                <UiButton
                  v-if="auth.hasPermission('course.publish')"
                  variant="ghost"
                  size="sm"
                  @click="togglePublish(c)"
                >
                  {{ c.status === 'published' ? t('courses.unpublish') : t('courses.publish') }}
                </UiButton>
                <UiButton
                  variant="ghost"
                  size="sm"
                  class="text-danger-600"
                  @click="handleDelete(c)"
                >
                  {{ t('common.delete') }}
                </UiButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </UiCard>

  <CourseDrawer
    :open="drawerOpen"
    :course="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
