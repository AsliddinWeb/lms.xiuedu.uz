<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import type { LiveSession, LiveStatus } from '@shared/types/live'

const { t, locale } = useI18n()

type Filter = LiveStatus | ''
const statusFilter = ref<Filter>('')
const q = ref('')

const items = ref<LiveSession[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const page = ref(1)
const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const stats = ref({ total: 0, scheduled: 0, live: 0, ended: 0, cancelled: 0 })
async function loadStats() {
  const count = (status?: LiveStatus) =>
    liveSessionsApi.list({ status, page_size: 1 }).then((r) => r.total).catch(() => 0)
  const [tot, sch, lv, en, can] = await Promise.all([
    count(), count('scheduled'), count('live'), count('ended'), count('cancelled'),
  ])
  stats.value = { total: tot, scheduled: sch, live: lv, ended: en, cancelled: can }
}

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
      page: page.value,
      page_size: pageSize,
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
  qTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 250)
})
watch(page, load)

onMounted(() => {
  void loadStats()
  void load()
})

function fmtDateTime(s: string): string {
  try {
    return formatDate(s, locale.value, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return s
  }
}

function statusVariant(s: LiveStatus): 'default' | 'success' | 'warning' {
  if (s === 'live') return 'success'
  if (s === 'cancelled') return 'warning'
  return 'default'
}

// CSV eksport — joriy filtr bo'yicha barcha darslar
const exporting = ref(false)
function csvCell(v: string): string {
  return `"${String(v).replace(/"/g, '""')}"`
}
async function exportCsv() {
  exporting.value = true
  try {
    const all = await liveSessionsApi.list({
      status: statusFilter.value || undefined,
      q: q.value || undefined,
      page: 1,
      page_size: 1000,
    })
    const headers = [
      t('live.col_title'), t('live.col_start'), t('live.col_duration'),
      t('admin_live.col_host'), t('live.col_provider'), t('live.col_status'),
      t('admin_live.col_recording'),
    ]
    const lines = [headers.map(csvCell).join(',')]
    for (const s of all.items) {
      lines.push([
        s.title, s.scheduled_start.slice(0, 16).replace('T', ' '),
        `${s.duration_minutes} ${t('admin_live.minutes_short')}`,
        s.host_full_name ?? `#${s.host_user_id}`, s.provider,
        t(`live.status_${s.status}`), s.recording_url ? t('admin_live.recording_yes') : '—',
      ].map(csvCell).join(','))
    }
    const csv = '﻿' + lines.join('\r\n')
    downloadBlob(new Blob([csv], { type: 'text/csv;charset=utf-8' }), timestampedFilename('live_darslar'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.load_error')))
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_live.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_live.title') }}</h1>
      <p class="page-subtitle">{{ t('admin_live.subtitle') }}</p>
    </div>
    <UiButton variant="outline" :loading="exporting" @click="exportCsv">
      {{ t('admin_live.export_csv') }}
    </UiButton>
  </div>

  <!-- KPI -->
  <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
    <UiStatCard :label="t('admin_live.kpi_total')" :value="String(stats.total)" />
    <UiStatCard :label="t('live.status_scheduled')" :value="String(stats.scheduled)" />
    <UiStatCard :label="t('live.status_live')" :value="String(stats.live)" :tone="stats.live > 0 ? 'success' : 'default'" />
    <UiStatCard :label="t('live.status_ended')" :value="String(stats.ended)" />
    <UiStatCard :label="t('live.status_cancelled')" :value="String(stats.cancelled)" />
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
      <thead class="bg-muted text-[11px] uppercase tracking-wider text-muted-foreground">
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
          <td class="px-4 py-3 font-mono">{{ s.duration_minutes }} {{ t('admin_live.minutes_short') }}</td>
          <td class="px-4 py-3 text-[12px]">
            {{ s.host_full_name ?? `#${s.host_user_id}` }}
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
</template>
