<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { assignmentsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { Assignment, Submission, SubmissionStatus } from '@shared/types/assignments'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const items = ref<Submission[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const assignmentTitles = ref<Record<number, string>>({})

type Filter = 'pending' | 'grading' | 'graded' | 'all'
const filter = ref<Filter>('pending')
const searchQ = ref('')
const pendingCount = ref(0)

// Talaba nomi bo'yicha mahalliy filtr (yuklangan ro'yxat ustidan)
const displayedItems = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((s) =>
    (s.user_full_name ?? `#${s.user_id}`).toLowerCase().includes(q),
  )
})

const assignmentIdParam = computed(() => {
  const v = route.query.assignment_id
  if (typeof v === 'string') {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  return null
})

function statusFromFilter(f: Filter): SubmissionStatus | undefined {
  if (f === 'pending') return 'submitted'
  if (f === 'grading') return 'grading'
  if (f === 'graded') return 'graded'
  return undefined
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await assignmentsApi.inbox({
      status: statusFromFilter(filter.value),
      assignment_id: assignmentIdParam.value ?? undefined,
      page_size: 100,
    })
    items.value = data.items
    total.value = data.total

    const aIds = Array.from(new Set(items.value.map((s) => s.assignment_id)))
    const missingA = aIds.filter((id) => !(id in assignmentTitles.value))
    await Promise.all(
      missingA.map(async (id) => {
        try {
          const a: Assignment = await assignmentsApi.get(id)
          assignmentTitles.value = {
            ...assignmentTitles.value,
            [id]: a.title,
          }
        } catch {
          assignmentTitles.value = {
            ...assignmentTitles.value,
            [id]: `#${id}`,
          }
        }
      }),
    )
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function loadPendingCount() {
  try {
    const data = await assignmentsApi.inbox({
      status: 'submitted',
      assignment_id: assignmentIdParam.value ?? undefined,
      page_size: 1,
    })
    pendingCount.value = data.total
  } catch {
    // ignore
  }
}

onMounted(() => {
  load()
  loadPendingCount()
})
watch([filter, assignmentIdParam], load)
watch(assignmentIdParam, loadPendingCount)

function fmtDateTime(s: string): string {
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}

function statusVariant(s: SubmissionStatus): 'default' | 'success' | 'warning' {
  if (s === 'graded') return 'success'
  if (s === 'returned') return 'warning'
  return 'default'
}

function open(s: Submission) {
  router.push({ name: 'grade-submission', params: { id: s.id } })
}
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('grading_inbox.title')]"
    class="mb-6"
  />
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('grading_inbox.title') }}</h1>
      <p class="page-subtitle">{{ t('grading_inbox.subtitle') }}</p>
    </div>
    <UiBadge :variant="pendingCount > 0 ? 'warning' : 'success'" with-dot>
      {{ t('grading_inbox.ungraded', { n: pendingCount }) }}
    </UiBadge>
  </div>

  <!-- Filter row (wireframe 14 pattern) -->
  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="flex items-center gap-1">
      <button
        v-for="opt in (['pending', 'grading', 'graded', 'all'] as Filter[])"
        :key="opt"
        type="button"
        class="px-3 py-1.5 rounded-md text-[12px] font-medium border transition-colors"
        :class="
          filter === opt
            ? 'bg-foreground text-background border-foreground'
            : 'bg-background text-foreground border-border-strong hover:bg-muted'
        "
        @click="filter = opt"
      >
        {{ t(`grading_inbox.filter_${opt}`) }}
      </button>
    </div>
    <div class="w-px h-7 bg-border mx-1" aria-hidden="true"></div>
    <div class="flex-1 min-w-[200px] max-w-[320px]">
      <UiInput
        v-model="searchQ"
        type="search"
        :placeholder="t('grading_inbox.search_student')"
      />
    </div>
    <span class="ml-auto font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
      {{ displayedItems.length }} / {{ total }} {{ t('grading_inbox.total_short') }}
    </span>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="displayedItems.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('grading_inbox.no_items') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead class="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
        <tr>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_student') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_assignment') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_submitted') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_attempt') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_status') }}</th>
          <th scope="col" class="px-4 py-2.5"></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="s in displayedItems" :key="s.id" class="hover:bg-muted/30">
          <td class="px-4 py-3 font-medium">
            {{ s.user_full_name ?? `#${s.user_id}` }}
          </td>
          <td class="px-4 py-3 truncate max-w-[280px]">
            {{ assignmentTitles[s.assignment_id] ?? `#${s.assignment_id}` }}
          </td>
          <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
            {{ fmtDateTime(s.submitted_at) }}
            <span v-if="s.is_late" class="text-warning-600 ml-1">
              {{ t('grading_inbox.days_late', { n: s.days_late }) }}
            </span>
          </td>
          <td class="px-4 py-3 font-mono">#{{ s.attempt_number }}</td>
          <td class="px-4 py-3">
            <UiBadge :variant="statusVariant(s.status)" with-dot>
              {{ t(`assignments.status_${s.status}`) }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 text-right">
            <UiButton variant="outline" size="sm" @click="open(s)">
              {{ t('grading_inbox.review') }}
            </UiButton>
          </td>
        </tr>
      </tbody>
    </table>
  </UiCard>
</template>
