<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { formatDate } from '@shared/utils/datetime'
import { coursesApi } from '@shared/api/courses'
import { usersApi } from '@shared/api/users'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import CourseDrawer from '@shared/components/courses/CourseDrawer.vue'
import type { Course, CourseStatus, CourseType } from '@shared/types/courses'

const { t, locale } = useI18n()
const router = useRouter()

const drawerOpen = ref(false)
const editing = ref<Course | null>(null)
function openCreate() {
  editing.value = null
  drawerOpen.value = true
}
function openEdit(c: Course) {
  editing.value = c
  drawerOpen.value = true
}
function onSaved() {
  toast.success(t('common.saved'))
  void load()
  void loadStats()
}

const items = ref<Course[]>([])
const authorNames = ref<Record<number, string>>({})
const loading = ref(false)
const error = ref<string | null>(null)

const searchQ = ref('')
const statusFilter = ref<CourseStatus | ''>('')
const typeFilter = ref<CourseType | ''>('')

const page = ref(1)
const pageSize = 20
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

// KPI (filtrdan mustaqil — barcha kurslar bo'yicha)
const stats = ref({ total: 0, published: 0, draft: 0, archived: 0 })
async function loadStats() {
  const count = (status?: CourseStatus) =>
    coursesApi.list({ status, page: 1, page_size: 1 }).then((r) => r.total).catch(() => 0)
  const [tot, pub, dr, arc] = await Promise.all([
    count(), count('published'), count('draft'), count('archived'),
  ])
  stats.value = { total: tot, published: pub, draft: dr, archived: arc }
}

const statusOptions = computed(() => [
  { value: '' as CourseStatus | '', label: t('admin_courses.all_statuses') },
  { value: 'draft', label: t('courses.status_draft') },
  { value: 'published', label: t('courses.status_published') },
  { value: 'archived', label: t('courses.status_archived') },
])

const typeOptions = computed(() => [
  { value: '' as CourseType | '', label: t('admin_courses.all_types') },
  { value: 'academic', label: t('courses.type_academic') },
  { value: 'open', label: t('courses.type_open') },
  { value: 'micro', label: t('courses.type_micro') },
  { value: 'specialization', label: t('courses.type_specialization') },
])

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await coursesApi.list({
      status: statusFilter.value || undefined,
      type: typeFilter.value || undefined,
      q: searchQ.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = data.items
    total.value = data.total

    // Lookup authors (kichik N — bir martalik fetch yetadi)
    const authorIds = Array.from(
      new Set(items.value.map((c) => c.primary_author_id).filter((v): v is number => v !== null)),
    )
    const missing = authorIds.filter((id) => !(id in authorNames.value))
    await Promise.all(
      missing.map(async (id) => {
        try {
          const u = await usersApi.get(id)
          authorNames.value = { ...authorNames.value, [id]: u.full_name }
        } catch {
          authorNames.value = { ...authorNames.value, [id]: `#${id}` }
        }
      }),
    )
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadStats()
  void load()
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchQ, statusFilter, typeFilter], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 250)
})
watch(page, load)

function statusVariant(s: CourseStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function authorLabel(c: Course): string {
  if (c.primary_author_id == null) return '—'
  return authorNames.value[c.primary_author_id] ?? `#${c.primary_author_id}`
}

function fmtDate(s: string): string {
  return formatDate(s, locale.value, { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_courses.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_courses.title') }}</h1>
      <p class="page-subtitle">{{ t('admin_courses.subtitle') }}</p>
    </div>
    <UiButton v-permission="'course.create'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('courses.drawer_new_title') }}
    </UiButton>
  </div>

  <!-- KPI -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
    <UiStatCard :label="t('admin_courses.kpi_total')" :value="String(stats.total)" />
    <UiStatCard :label="t('courses.status_published')" :value="String(stats.published)" tone="success" />
    <UiStatCard :label="t('courses.status_draft')" :value="String(stats.draft)" />
    <UiStatCard :label="t('courses.status_archived')" :value="String(stats.archived)" :tone="stats.archived > 0 ? 'warning' : 'default'" />
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="p-4 grid grid-cols-1 md:grid-cols-[1fr_180px_180px] gap-3">
      <input
        v-model="searchQ"
        :placeholder="t('admin_courses.search_placeholder')"
        class="rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
      />
      <UiSelect v-model="statusFilter" :options="statusOptions" />
      <UiSelect v-model="typeFilter" :options="typeOptions" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('admin_courses.no_courses') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead class="bg-muted text-[11px] uppercase tracking-wider text-muted-foreground">
        <tr>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_title') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_author') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_type') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_students') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_status') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_created') }}</th>
          <th scope="col" class="px-4 py-2.5"></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="c in items" :key="c.id" class="hover:bg-muted/30">
          <td class="px-4 py-3">
            <div class="font-medium text-foreground">{{ c.title }}</div>
            <div class="font-mono text-[11px] text-muted-foreground mt-0.5">/{{ c.slug }}</div>
          </td>
          <td class="px-4 py-3">{{ authorLabel(c) }}</td>
          <td class="px-4 py-3">
            <UiBadge variant="default">{{ t(`courses.type_${c.type}`) }}</UiBadge>
          </td>
          <td class="px-4 py-3 font-mono text-[12px] tabular-nums">{{ c.enrollment_count ?? '—' }}</td>
          <td class="px-4 py-3">
            <UiBadge :variant="statusVariant(c.status)" with-dot>
              {{ t(`courses.status_${c.status}`) }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 font-mono text-[11px] text-muted-foreground">{{ fmtDate(c.created_at) }}</td>
          <td class="px-4 py-3 text-right whitespace-nowrap">
            <UiButton
              v-permission="'course.edit'"
              variant="ghost"
              size="sm"
              class="mr-1"
              @click="openEdit(c)"
            >
              {{ t('common.edit') }}
            </UiButton>
            <UiButton
              variant="outline"
              size="sm"
              @click="router.push({ name: 'admin-course-detail', params: { id: c.id } })"
            >
              {{ t('admin_courses.open_detail') }}
            </UiButton>
          </td>
        </tr>
      </tbody>
    </table>

    <div
      v-if="items.length > 0"
      class="flex items-center justify-between px-4 py-3 border-t border-border text-[12px] text-muted-foreground"
    >
      <div>
        {{ t('common.total') }}: <span class="font-mono text-foreground">{{ total }}</span> ·
        {{ t('common.page') }} <span class="font-mono text-foreground">{{ page }}</span> /
        <span class="font-mono">{{ totalPages }}</span>
      </div>
      <div class="flex gap-2">
        <UiButton variant="outline" size="sm" :disabled="page <= 1 || loading" @click="page--">← {{ t('common.prev') }}</UiButton>
        <UiButton variant="outline" size="sm" :disabled="page >= totalPages || loading" @click="page++">{{ t('common.next') }} →</UiButton>
      </div>
    </div>
  </UiCard>

  <CourseDrawer
    :open="drawerOpen"
    :course="editing"
    @close="drawerOpen = false"
    @saved="onSaved"
  />
</template>
