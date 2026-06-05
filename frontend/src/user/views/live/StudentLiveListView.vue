<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import type { LiveSession, LiveStatus } from '@shared/types/live'

import LiveCalendarButton from '@user/components/live/LiveCalendarButton.vue'

const { t, locale } = useI18n()
const router = useRouter()

type Filter = 'all' | 'live_now' | 'upcoming' | 'past'
const filter = ref<Filter>('all')
const searchQ = ref('')

const items = ref<LiveSession[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    // Barchasini bir martada olamiz — stat'lar va filtrlar uchun
    const data = await liveSessionsApi.list({ page_size: 100 })
    items.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

const counts = computed(() => {
  const c = { all: items.value.length, live_now: 0, upcoming: 0, past: 0 }
  const now = Date.now()
  for (const s of items.value) {
    if (s.status === 'live') c.live_now++
    else if (s.status === 'scheduled' && new Date(s.scheduled_start).getTime() > now)
      c.upcoming++
    else if (s.status === 'ended') c.past++
  }
  return c
})

const filtered = computed(() => {
  let list = items.value
  const now = Date.now()
  if (filter.value === 'live_now') list = list.filter((s) => s.status === 'live')
  else if (filter.value === 'upcoming')
    list = list.filter(
      (s) =>
        s.status === 'scheduled' &&
        new Date(s.scheduled_start).getTime() > now,
    )
  else if (filter.value === 'past') list = list.filter((s) => s.status === 'ended')

  const q = searchQ.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        (s.description ?? '').toLowerCase().includes(q),
    )
  }

  return [...list].sort((a, b) => {
    const order: Record<LiveStatus, number> = {
      live: 0,
      scheduled: 1,
      ended: 2,
      cancelled: 3,
    }
    if (order[a.status] !== order[b.status]) {
      return order[a.status] - order[b.status]
    }
    return (
      new Date(b.scheduled_start).getTime() -
      new Date(a.scheduled_start).getTime()
    )
  })
})

function fmtDateTime(s: string): string {
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      weekday: 'short',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}

function relativeStart(s: LiveSession): string {
  const start = new Date(s.scheduled_start).getTime()
  const diffMs = start - Date.now()
  const abs = Math.abs(diffMs)
  const mins = Math.floor(abs / 60000)
  const hrs = Math.floor(mins / 60)
  const days = Math.floor(hrs / 24)
  if (s.status === 'live') return t('live.row_in_progress')
  if (s.status === 'ended') {
    if (days > 0) return t('live.row_days_ago', { n: days })
    if (hrs > 0) return t('live.row_hours_ago', { n: hrs })
    return t('live.row_recent')
  }
  if (diffMs < 0) return fmtDateTime(s.scheduled_start)
  if (mins < 60) return t('live.row_in_minutes', { n: mins })
  if (hrs < 24) return t('live.row_in_hours', { n: hrs })
  if (days < 7) return t('live.row_in_days', { n: days })
  return fmtDateTime(s.scheduled_start)
}

function statusVariant(s: LiveStatus): 'default' | 'success' | 'warning' {
  if (s === 'live') return 'success'
  if (s === 'cancelled') return 'warning'
  return 'default'
}

function joinRoom(s: LiveSession) {
  router.push({ name: 'live-lobby', params: { id: s.id } })
}

function goToDetail(s: LiveSession) {
  router.push({ name: 'live-room', params: { id: s.id } })
}
</script>

<template>
  <UiBreadcrumb
    :items="[
      { label: t('dashboard.crumb_home'), to: '/app/dashboard' },
      t('live.title_student'),
    ]"
    class="mb-6"
  />
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('live.title_student') }}</h1>
      <p class="page-subtitle">{{ t('live.subtitle_student') }}</p>
    </div>
    <LiveCalendarButton />
  </div>

  <!-- Stat grid -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
    <UiStatCard
      :label="t('live.stat_total')"
      :value="String(counts.all)"
    />
    <UiStatCard
      :label="t('live.stat_live_now')"
      :value="String(counts.live_now)"
      :tone="counts.live_now > 0 ? 'success' : 'default'"
    />
    <UiStatCard
      :label="t('live.stat_upcoming')"
      :value="String(counts.upcoming)"
    />
    <UiStatCard
      :label="t('live.stat_past')"
      :value="String(counts.past)"
    />
  </div>

  <!-- Filter row -->
  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="flex items-center gap-1">
      <button
        v-for="opt in (['all', 'live_now', 'upcoming', 'past'] as Filter[])"
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
        {{ t(`live.filter_${opt}`) }}
        <span
          v-if="opt !== 'all'"
          class="ml-1 font-mono text-[10px] opacity-70"
        >({{ counts[opt] }})</span>
      </button>
    </div>
    <div class="w-px h-7 bg-border mx-1" aria-hidden="true"></div>
    <div class="flex-1 min-w-[200px] max-w-[320px]">
      <UiInput
        v-model="searchQ"
        type="search"
        :placeholder="t('live.search_placeholder')"
      />
    </div>
    <span class="ml-auto font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
      {{ filtered.length }} {{ t('grading_inbox.total_short') }}
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
    {{ items.length === 0 ? t('live.no_sessions_upcoming') : t('live.no_filter_match') }}
  </div>

  <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
    <UiCard v-for="s in filtered" :key="s.id">
      <template #header>
        <div class="min-w-0">
          <h3 class="text-base font-semibold text-foreground truncate">{{ s.title }}</h3>
          <div class="text-[12px] text-foreground mt-0.5">{{ relativeStart(s) }}</div>
          <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
            {{ fmtDateTime(s.scheduled_start) }} · {{ s.duration_minutes }} {{ t('live.min_short') }}
          </div>
        </div>
        <UiBadge :variant="statusVariant(s.status)" with-dot>
          {{ t(`live.status_${s.status}`) }}
        </UiBadge>
      </template>

      <p
        v-if="s.description"
        class="text-[12.5px] text-muted-foreground line-clamp-2 mb-3"
      >
        {{ s.description }}
      </p>

      <div
        v-if="s.recording_url"
        class="flex items-center gap-1.5 text-[11.5px] text-success-600 mb-2"
      >
        <span>●</span>
        <span class="font-mono">{{ t('live.recording_available') }}</span>
      </div>

      <template #actions>
        <UiButton
          v-if="s.status === 'live'"
          @click="joinRoom(s)"
        >
          ▶ {{ t('live.btn_join_now') }}
        </UiButton>
        <UiButton
          v-else-if="s.status === 'scheduled'"
          variant="outline"
          size="sm"
          @click="goToDetail(s)"
        >
          {{ t('live.btn_detail') }}
        </UiButton>
        <UiButton
          v-else-if="s.status === 'ended' && s.recording_url"
          variant="outline"
          size="sm"
          @click="goToDetail(s)"
        >
          ▶ {{ t('live.btn_view_recording') }}
        </UiButton>
        <UiButton
          v-else-if="s.status === 'ended'"
          variant="outline"
          size="sm"
          @click="goToDetail(s)"
        >
          {{ t('live.btn_detail') }}
        </UiButton>
        <UiButton
          v-else-if="s.status === 'cancelled'"
          variant="ghost"
          size="sm"
          disabled
        >
          {{ t('live.status_cancelled') }}
        </UiButton>
      </template>
    </UiCard>
  </div>
</template>
