<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import type { LiveSession, LiveStatus } from '@shared/types/live'

const { t, locale } = useI18n()

type Filter = LiveStatus | ''
const statusFilter = ref<Filter>('')
const q = ref('')

const items = ref<LiveSession[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const statusOptions = [
  { value: '' as Filter, label: t('live.all_statuses') },
  { value: 'scheduled' as Filter, label: t('live.status_scheduled') },
  { value: 'live' as Filter, label: t('live.status_live') },
  { value: 'ended' as Filter, label: t('live.status_ended') },
  { value: 'cancelled' as Filter, label: t('live.status_cancelled') },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await liveSessionsApi.list({
      status: statusFilter.value || undefined,
      q: q.value || undefined,
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

let qTimer: ReturnType<typeof setTimeout> | null = null
watch([statusFilter, q], () => {
  if (qTimer) clearTimeout(qTimer)
  qTimer = setTimeout(load, 250)
})

onMounted(load)

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

function statusVariant(s: LiveStatus): 'default' | 'success' | 'warning' {
  if (s === 'live') return 'success'
  if (s === 'cancelled') return 'warning'
  return 'default'
}
</script>

<template>
  <div class="mb-6">
    <UiBreadcrumb :items="['Admin', t('admin_live.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_live.title') }}</h1>
    <p class="page-subtitle">{{ t('admin_live.subtitle') }}</p>
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="p-4 grid grid-cols-1 md:grid-cols-[1fr_220px] gap-3">
      <UiInput
        v-model="q"
        type="search"
        :placeholder="t('admin_live.search_placeholder')"
      />
      <UiSelect v-model="statusFilter" :options="statusOptions" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('admin_live.no_sessions') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead class="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
        <tr>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('live.col_title') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('live.col_start') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('live.col_duration') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_live.col_host') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('live.col_provider') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('live.col_status') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_live.col_recording') }}</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="s in items" :key="s.id" class="hover:bg-muted/30">
          <td class="px-4 py-3">
            <div class="font-medium">{{ s.title }}</div>
            <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
              #{{ s.id }}
            </div>
          </td>
          <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
            {{ fmtDateTime(s.scheduled_start) }}
          </td>
          <td class="px-4 py-3 font-mono">{{ s.duration_minutes }} min</td>
          <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
            #{{ s.host_user_id }}
          </td>
          <td class="px-4 py-3">
            <UiBadge variant="default">{{ s.provider }}</UiBadge>
          </td>
          <td class="px-4 py-3">
            <UiBadge :variant="statusVariant(s.status)" with-dot>
              {{ t(`live.status_${s.status}`) }}
            </UiBadge>
          </td>
          <td class="px-4 py-3">
            <a
              v-if="s.recording_url"
              :href="s.recording_url"
              target="_blank"
              rel="noopener"
              class="font-mono text-[11px] text-foreground underline decoration-dotted hover:text-muted-foreground"
            >
              {{ t('admin_live.recording_yes') }}
            </a>
            <span v-else class="font-mono text-[11px] text-muted-foreground">
              —
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </UiCard>
</template>
