<script setup lang="ts">
/**
 * Admin — live dars tafsilotlari (read-only) + davomat + moderatsiya.
 * Pedagog dars yaratadi/o'tkazadi; admin nazorat qiladi (bekor/tugatish/o'chirish).
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import { liveSessionsApi } from '@shared/api/live'
import type { AttendanceSummary, LiveSession, LiveStatus } from '@shared/types/live'

interface Props {
  open: boolean
  session: LiveSession | null
  acting?: boolean
}
const props = withDefaults(defineProps<Props>(), { acting: false })
const emit = defineEmits<{
  close: []
  cancel: []
  end: []
  remove: []
}>()

const { t, locale } = useI18n()

const summary = ref<AttendanceSummary | null>(null)
const summaryLoading = ref(false)

watch(
  () => [props.open, props.session?.id],
  async () => {
    summary.value = null
    if (!props.open || !props.session) return
    summaryLoading.value = true
    try {
      summary.value = await liveSessionsApi.getAttendanceSummary(props.session.id)
    } catch {
      summary.value = null
    } finally {
      summaryLoading.value = false
    }
  },
  { immediate: true },
)

function statusVariant(s: LiveStatus): 'default' | 'success' | 'warning' {
  if (s === 'live') return 'success'
  if (s === 'cancelled') return 'warning'
  return 'default'
}

function humanFileSize(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let v = bytes / 1024
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(1)} ${units[i]}`
}

function fmt(s: string | null | undefined): string {
  if (!s) return '—'
  return formatDate(s, locale.value, {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <UiDrawer :open="open" :title="t('admin_live.detail_title')" width="lg" @close="emit('close')">
    <template v-if="session">
      <!-- Sarlavha + status -->
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-2 flex-wrap">
          <UiBadge :variant="statusVariant(session.status)" with-dot>
            {{ t(`live.status_${session.status}`) }}
          </UiBadge>
          <UiBadge variant="default">{{ session.provider }}</UiBadge>
          <span class="font-mono text-[11px] text-muted-foreground">#{{ session.id }}</span>
        </div>
        <h3 class="text-[15px] font-semibold text-foreground">{{ session.title }}</h3>
        <p v-if="session.description" class="text-[13px] text-muted-foreground mt-1">
          {{ session.description }}
        </p>
      </div>

      <!-- Jadval / metadata -->
      <dl class="text-[13px] grid grid-cols-2 gap-x-6 gap-y-2 mb-5">
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('admin_live.col_host') }}</dt>
          <dd class="truncate">{{ session.host_full_name ?? `#${session.host_user_id}` }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('live.col_duration') }}</dt>
          <dd class="font-mono">{{ session.duration_minutes }} {{ t('admin_live.minutes_short') }}</dd>
        </div>
        <div class="flex justify-between gap-3 col-span-2">
          <dt class="text-muted-foreground">{{ t('admin_live.f_scheduled') }}</dt>
          <dd class="font-mono text-[11px]">{{ fmt(session.scheduled_start) }} — {{ fmt(session.scheduled_end) }}</dd>
        </div>
        <div v-if="session.actual_start" class="flex justify-between gap-3 col-span-2">
          <dt class="text-muted-foreground">{{ t('admin_live.f_actual') }}</dt>
          <dd class="font-mono text-[11px]">{{ fmt(session.actual_start) }} — {{ fmt(session.actual_end) }}</dd>
        </div>
        <div v-if="session.provider_meeting_id" class="flex justify-between gap-3 col-span-2">
          <dt class="text-muted-foreground">{{ t('admin_live.f_meeting_id') }}</dt>
          <dd class="font-mono text-[11px] truncate">{{ session.provider_meeting_id }}</dd>
        </div>
      </dl>

      <!-- Davomat -->
      <div class="mono-tag mb-2">{{ t('admin_live.f_attendance') }}</div>
      <div v-if="summaryLoading" class="text-[12px] text-muted-foreground mb-5">{{ t('common.loading') }}</div>
      <dl v-else-if="summary" class="text-[13px] grid grid-cols-3 gap-x-6 gap-y-2 mb-5">
        <div class="text-center">
          <div class="text-[18px] font-semibold tabular-nums">{{ summary.joined_participants }}</div>
          <div class="text-[10px] uppercase tracking-wider text-muted-foreground">{{ t('admin_live.f_participants') }}</div>
        </div>
        <div class="text-center">
          <div class="text-[18px] font-semibold tabular-nums">{{ summary.counted_participants }} ({{ summary.counted_percent }}%)</div>
          <div class="text-[10px] uppercase tracking-wider text-muted-foreground">{{ t('admin_live.f_counted') }}</div>
        </div>
        <div class="text-center">
          <div class="text-[18px] font-semibold tabular-nums">{{ summary.average_minutes }}</div>
          <div class="text-[10px] uppercase tracking-wider text-muted-foreground">{{ t('admin_live.f_avg_minutes') }}</div>
        </div>
      </dl>
      <div v-else class="text-[12px] text-muted-foreground italic mb-5">{{ t('admin_live.no_attendance') }}</div>

      <!-- Yozuv -->
      <template v-if="session.recording_url">
        <div class="mono-tag mb-2">{{ t('admin_live.f_recording') }}</div>
        <div class="flex items-center gap-3 mb-2">
          <a
            :href="session.recording_url"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center justify-center rounded-md border border-border-strong bg-background text-foreground hover:bg-muted px-3 py-1.5 text-xs font-medium transition-colors"
          >
            {{ t('admin_live.recording_yes') }} ↗
          </a>
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ humanFileSize(session.recording_size_bytes) }}
          </span>
        </div>
      </template>
    </template>

    <template #footer>
      <div class="flex items-center justify-between gap-2 w-full">
        <UiButton
          v-permission="'live.host'"
          variant="ghost"
          size="sm"
          class="text-danger-600"
          :loading="acting"
          @click="emit('remove')"
        >
          {{ t('admin_live.action_delete') }}
        </UiButton>
        <div class="flex items-center gap-2">
          <UiButton variant="outline" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
          <UiButton
            v-if="session && session.status === 'live'"
            v-permission="'live.host'"
            :loading="acting"
            @click="emit('end')"
          >
            {{ t('admin_live.action_end') }}
          </UiButton>
          <UiButton
            v-if="session && session.status === 'scheduled'"
            v-permission="'live.host'"
            variant="outline"
            :loading="acting"
            @click="emit('cancel')"
          >
            {{ t('admin_live.action_cancel') }}
          </UiButton>
        </div>
      </div>
    </template>
  </UiDrawer>
</template>
