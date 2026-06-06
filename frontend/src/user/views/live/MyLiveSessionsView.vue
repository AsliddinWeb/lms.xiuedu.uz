<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { useAuthStore } from '@shared/stores/auth'
import type { LiveSession, LiveStatus } from '@shared/types/live'

import LiveSessionDrawer from '@user/components/live/LiveSessionDrawer.vue'
import LiveCalendarButton from '@user/components/live/LiveCalendarButton.vue'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

type Filter = LiveStatus | 'all'
const filter = ref<Filter>('all')  // Wireframe-style: hammasi default
const searchQ = ref('')

const items = ref<LiveSession[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const drawerOpen = ref(false)
const editing = ref<LiveSession | null>(null)

// Upload state (recording upload for ended sessions)
const uploadingForId = ref<number | null>(null)
const uploadProgress = ref(0)

async function load() {
  loading.value = true
  error.value = null
  try {
    // Hammasini olamiz — stat'lar uchun kerak
    const data = await liveSessionsApi.list({
      host_user_id: auth.user?.id,
      page_size: 100,
    })
    items.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

// Status bo'yicha hisoblash
const counts = computed(() => {
  const c = { all: items.value.length, scheduled: 0, live: 0, ended: 0, cancelled: 0 }
  for (const s of items.value) {
    c[s.status]++
  }
  return c
})

// Filtered + searched
const filtered = computed(() => {
  let list = items.value
  if (filter.value !== 'all') {
    list = list.filter((s) => s.status === filter.value)
  }
  const q = searchQ.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        (s.description ?? '').toLowerCase().includes(q),
    )
  }
  // Tartib: live → scheduled → ended (yangidan eskiga) → cancelled
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

watch([filter, searchQ], () => {
  // sync filterga reload kerak emas — clientda filterlanadi
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}

function openEdit(s: LiveSession) {
  editing.value = s
  drawerOpen.value = true
}

function onSaved() {
  void load()
}

async function onCancel(s: LiveSession) {
  const ok = await confirm({
    title: t('live.confirm_cancel'),
    description: s.title,
    variant: 'danger',
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await liveSessionsApi.cancel(s.id)
    await load()
    toast.success(t('common.saved'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

async function onDelete(s: LiveSession) {
  const ok = await confirm({
    title: t('live.confirm_delete'),
    description: s.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await liveSessionsApi.remove(s.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

async function onDeleteRecording(s: LiveSession) {
  const ok = await confirm({
    title: t('live.confirm_delete_recording'),
    description: s.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await liveSessionsApi.deleteRecording(s.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

// Row click → detail (lobby live'lar uchun, room ended/cancelled uchun)
function goToSession(s: LiveSession) {
  if (s.status === 'live' || s.status === 'scheduled') {
    router.push({ name: 'live-lobby', params: { id: s.id } })
  } else {
    // Ended / cancelled — LiveRoomView non-live state ko'rsatadi (summary + recording)
    router.push({ name: 'live-room', params: { id: s.id } })
  }
}

async function copyLink(s: LiveSession) {
  const url = `${window.location.origin}/app/live/${s.id}/lobby`
  try {
    await navigator.clipboard.writeText(url)
    toast.success(t('live.link_copied'))
  } catch {
    toast.error(t('common.save_error'))
  }
}

// File upload for ended session recording
const fileInputs = ref<Record<number, HTMLInputElement | null>>({})
function triggerUpload(s: LiveSession) {
  fileInputs.value[s.id]?.click()
}
async function onRecordingFile(s: LiveSession, ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingForId.value = s.id
  uploadProgress.value = 0
  try {
    await liveSessionsApi.uploadRecording(s.id, file, (loaded, total) => {
      uploadProgress.value = Math.round((loaded / total) * 100)
    })
    await load()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    uploadingForId.value = null
    uploadProgress.value = 0
    if (input) input.value = ''
  }
}

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

function statusVariant(s: LiveStatus): 'default' | 'success' | 'warning' | 'danger' {
  if (s === 'live') return 'success'
  if (s === 'cancelled') return 'warning'
  if (s === 'ended') return 'default'
  return 'default'
}
</script>

<template>
  <UiBreadcrumb
    :items="[
      { label: t('dashboard.crumb_home'), to: '/app/dashboard' },
      t('live.title_host'),
    ]"
    class="mb-6"
  />
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('live.title_host') }}</h1>
      <p class="page-subtitle">{{ t('live.subtitle_host') }}</p>
    </div>
    <div class="flex items-center gap-2">
      <LiveCalendarButton />
      <UiButton @click="openCreate">
        <svg
          width="14" height="14" viewBox="0 0 14 14" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round"
        >
          <path d="M7 2v10M2 7h10" />
        </svg>
        {{ t('live.new') }}
      </UiButton>
    </div>
  </div>

  <!-- Stat grid -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
    <UiStatCard
      :label="t('live.stat_total')"
      :value="String(counts.all)"
    />
    <UiStatCard
      :label="t('live.stat_live_now')"
      :value="String(counts.live)"
      :tone="counts.live > 0 ? 'success' : 'default'"
    />
    <UiStatCard
      :label="t('live.stat_upcoming')"
      :value="String(counts.scheduled)"
    />
    <UiStatCard
      :label="t('live.stat_ended')"
      :value="String(counts.ended)"
    />
  </div>

  <!-- Filter row -->
  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="flex items-center gap-1">
      <button
        v-for="opt in (['all', 'live', 'scheduled', 'ended', 'cancelled'] as Filter[])"
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
        >({{ counts[opt as LiveStatus] }})</span>
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

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div
      v-else-if="filtered.length === 0"
      class="p-12 text-center border border-dashed border-border rounded-lg m-4 text-muted-foreground"
    >
      {{ items.length === 0 ? t('live.no_sessions_host') : t('live.no_filter_match') }}
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('live.col_status') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('live.col_title') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('live.col_when') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('live.col_duration') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('live.col_recording') }}
            </th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in filtered"
            :key="s.id"
            class="border-t border-border hover:bg-muted/30 cursor-pointer"
            @click="goToSession(s)"
          >
            <td class="px-4 py-3 align-top">
              <UiBadge :variant="statusVariant(s.status)" with-dot>
                {{ t(`live.status_${s.status}`) }}
              </UiBadge>
            </td>
            <td class="px-4 py-3">
              <div class="font-medium">{{ s.title }}</div>
              <div
                v-if="s.description"
                class="text-[11px] text-muted-foreground line-clamp-1 mt-0.5"
              >
                {{ s.description }}
              </div>
            </td>
            <td class="px-4 py-3 align-top">
              <div class="text-[12.5px]">{{ relativeStart(s) }}</div>
              <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
                {{ fmtDateTime(s.scheduled_start) }}
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-[12px] align-top">
              {{ s.duration_minutes }} {{ t('live.min_short') }}
            </td>
            <td class="px-4 py-3 align-top">
              <div v-if="s.recording_url" class="flex items-center gap-1.5">
                <span class="text-success-600">●</span>
                <a
                  :href="s.recording_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-[12px] text-foreground hover:underline"
                  @click.stop
                >
                  {{ t('live.recording_download') }}
                </a>
              </div>
              <div
                v-else-if="s.is_recording_enabled && s.status === 'live'"
                class="flex items-center gap-1.5 text-[11px] font-mono text-danger-600"
              >
                <span class="rec-dot-mini"></span>
                {{ t('live.recording_active_short') }}
              </div>
              <div
                v-else-if="s.is_recording_enabled && s.status === 'scheduled'"
                class="text-[11px] text-muted-foreground font-mono"
              >
                {{ t('live.recording_planned') }}
              </div>
              <div
                v-else-if="s.status === 'ended'"
                class="text-[11px] text-muted-foreground font-mono"
              >
                {{ t('live.recording_none') }}
              </div>
              <div v-else class="text-[11px] text-muted-foreground">—</div>
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap align-top" @click.stop>
              <div class="flex justify-end gap-1.5 flex-wrap">
                <!-- Live / Scheduled — enter lobby -->
                <UiButton
                  v-if="s.status === 'scheduled' || s.status === 'live'"
                  variant="outline"
                  size="sm"
                  @click="goToSession(s)"
                >
                  {{ s.status === 'live' ? t('live.btn_resume') : t('live.btn_open') }}
                </UiButton>

                <!-- Havolani nusxalash (ulashish) -->
                <UiButton
                  v-if="s.status === 'scheduled' || s.status === 'live'"
                  variant="ghost"
                  size="sm"
                  @click="copyLink(s)"
                >
                  {{ t('live.btn_copy_link') }}
                </UiButton>

                <!-- Ended — detail view -->
                <UiButton
                  v-if="s.status === 'ended' || s.status === 'cancelled'"
                  variant="outline"
                  size="sm"
                  @click="goToSession(s)"
                >
                  {{ t('live.btn_detail') }}
                </UiButton>

                <!-- Upload recording (host) for ended without recording -->
                <template v-if="s.status === 'ended' && !s.recording_url">
                  <input
                    :ref="(el) => (fileInputs[s.id] = el as HTMLInputElement)"
                    type="file"
                    accept="video/*"
                    class="hidden"
                    @change="onRecordingFile(s, $event)"
                  />
                  <UiButton
                    variant="ghost"
                    size="sm"
                    :loading="uploadingForId === s.id"
                    @click="triggerUpload(s)"
                  >
                    {{ uploadingForId === s.id ? `${uploadProgress}%` : t('live.btn_upload_rec') }}
                  </UiButton>
                </template>

                <!-- Delete recording -->
                <UiButton
                  v-if="s.status === 'ended' && s.recording_url"
                  variant="ghost"
                  size="sm"
                  class="text-danger-600"
                  @click="onDeleteRecording(s)"
                >
                  {{ t('live.btn_delete_rec') }}
                </UiButton>

                <!-- Edit scheduled -->
                <UiButton
                  v-if="s.status === 'scheduled'"
                  variant="ghost"
                  size="sm"
                  @click="openEdit(s)"
                >
                  {{ t('common.edit') }}
                </UiButton>

                <!-- Cancel live/scheduled -->
                <UiButton
                  v-if="s.status === 'scheduled' || s.status === 'live'"
                  variant="ghost"
                  size="sm"
                  class="text-warning-600"
                  @click="onCancel(s)"
                >
                  {{ t('common.cancel') }}
                </UiButton>

                <!-- Delete -->
                <UiButton
                  v-if="s.status === 'scheduled' || s.status === 'cancelled'"
                  variant="ghost"
                  size="sm"
                  class="text-danger-600"
                  @click="onDelete(s)"
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

  <LiveSessionDrawer
    :open="drawerOpen"
    :session="editing"
    @close="drawerOpen = false"
    @saved="onSaved"
  />
</template>

<style scoped>
.rec-dot-mini {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(0.85); }
}
</style>
