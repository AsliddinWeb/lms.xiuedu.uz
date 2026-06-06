<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { appealsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { Appeal, AppealStatus } from '@shared/types/assignments'

import AppealRespondDrawer from '@user/components/grading/AppealRespondDrawer.vue'

const { t, locale } = useI18n()
const router = useRouter()

type Filter = AppealStatus | 'all'
const filter = ref<Filter>('pending')

const items = ref<Appeal[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const drawerOpen = ref(false)
const editing = ref<Appeal | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await appealsApi.list({
      status: filter.value === 'all' ? undefined : filter.value,
      page_size: 100,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(filter, load)

function openRespond(a: Appeal) {
  editing.value = a
  drawerOpen.value = true
}

function onResponded(updated: Appeal) {
  items.value = items.value.map((a) => (a.id === updated.id ? updated : a))
}

function fmtDate(s: string): string {
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

function statusVariant(
  s: AppealStatus,
): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'danger'
  if (s === 'pending') return 'info'
  return 'default'
}

function viewSubmission(a: Appeal) {
  router.push({ name: 'grade-submission', params: { id: a.submission_id } })
}
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('appeals.title_teacher')]"
    class="mb-6"
  />
  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('appeals.title_teacher') }}</h1>
    <p class="page-subtitle">{{ t('appeals.subtitle_teacher') }}</p>
  </div>

  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="flex items-center gap-1">
      <button
        v-for="opt in (['pending', 'approved', 'rejected', 'all'] as Filter[])"
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
        {{ t(`appeals.filter_${opt}`) }}
      </button>
    </div>
    <span class="ml-auto font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
      {{ total }} {{ t('grading_inbox.total_short') }}
    </span>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('appeals.no_appeals') }}
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grading_inbox.col_student') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('appeals.reason_label') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grading_inbox.col_status') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grading_inbox.col_submitted') }}
            </th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ap in items"
            :key="ap.id"
            class="border-t border-border hover:bg-muted/30"
          >
            <td class="px-4 py-3 font-medium align-top">
              {{ ap.student_full_name ?? `#${ap.student_id}` }}
            </td>
            <td class="px-4 py-3 max-w-[400px] align-top">
              <p class="line-clamp-2 text-[12.5px] text-muted-foreground">{{ ap.reason }}</p>
            </td>
            <td class="px-4 py-3 align-top">
              <UiBadge :variant="statusVariant(ap.status as AppealStatus)" with-dot>
                {{ t(`appeals.status_${ap.status}`) }}
              </UiBadge>
            </td>
            <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground align-top">
              {{ fmtDate(ap.created_at) }}
            </td>
            <td class="px-4 py-3 text-right align-top">
              <div class="flex justify-end gap-1.5">
                <UiButton variant="ghost" size="sm" @click="viewSubmission(ap)">
                  {{ t('appeals.view_submission') }}
                </UiButton>
                <UiButton
                  v-if="ap.status === 'pending'"
                  variant="outline"
                  size="sm"
                  @click="openRespond(ap)"
                >
                  {{ t('grading_inbox.review') }}
                </UiButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </UiCard>

  <AppealRespondDrawer
    :open="drawerOpen"
    :appeal="editing"
    @close="drawerOpen = false"
    @responded="onResponded"
  />
</template>
