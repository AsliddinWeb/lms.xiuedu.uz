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
import { coursesApi } from '@shared/api/courses'
import { usersApi } from '@shared/api/users'
import { extractErrorMessage } from '@shared/api/client'
import type { Course, CourseStatus, CourseType } from '@shared/types/courses'

const { t } = useI18n()
const router = useRouter()

const items = ref<Course[]>([])
const authorNames = ref<Record<number, string>>({})
const loading = ref(false)
const error = ref<string | null>(null)

const searchQ = ref('')
const statusFilter = ref<CourseStatus | ''>('')
const typeFilter = ref<CourseType | ''>('')

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
      page_size: 100,
    })
    items.value = data.items

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

onMounted(load)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchQ, statusFilter, typeFilter], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})

function statusVariant(s: CourseStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function authorLabel(c: Course): string {
  if (c.primary_author_id == null) return '—'
  return authorNames.value[c.primary_author_id] ?? `#${c.primary_author_id}`
}
</script>

<template>
  <div class="mb-6">
    <UiBreadcrumb :items="['Admin', t('admin_courses.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_courses.title') }}</h1>
    <p class="page-subtitle">{{ t('admin_courses.subtitle') }}</p>
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
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_enrollment') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_courses.col_status') }}</th>
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
          <td class="px-4 py-3">
            <span class="font-mono text-[12px]">{{ t(`courses.enrollment_${c.enrollment_type}`) }}</span>
          </td>
          <td class="px-4 py-3">
            <UiBadge :variant="statusVariant(c.status)" with-dot>
              {{ t(`courses.status_${c.status}`) }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 text-right">
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
  </UiCard>
</template>
