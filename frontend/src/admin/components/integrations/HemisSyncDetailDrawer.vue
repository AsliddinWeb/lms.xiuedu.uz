<script setup lang="ts">
/**
 * Admin — HEMIS sync log tafsilotlari (read-only): payload/response/error JSON.
 * Sync xatolarini debug qilish uchun.
 */
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '@shared/utils/datetime'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import type { HemisSyncLogItem } from '@shared/api/hemis'

interface Props {
  open: boolean
  log: HemisSyncLogItem | null
  typeLabel?: string
  statusLabel?: string
}
withDefaults(defineProps<Props>(), { typeLabel: '', statusLabel: '' })
const emit = defineEmits<{ close: []; retry: [] }>()

const { t, locale } = useI18n()

function statusVariant(s: string): 'default' | 'success' | 'warning' | 'danger' {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'retrying' || s === 'pending') return 'warning'
  return 'default'
}

function fmt(s: string | null | undefined): string {
  if (!s) return '—'
  try {
    return formatDateTime(s, locale.value)
  } catch {
    return s
  }
}

function pretty(obj: Record<string, unknown> | null): string {
  if (!obj || Object.keys(obj).length === 0) return ''
  return JSON.stringify(obj, null, 2)
}
</script>

<template>
  <UiDrawer :open="open" :title="t('hemis_log.detail_title')" width="lg" @close="emit('close')">
    <template v-if="log">
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-2 flex-wrap">
          <UiBadge :variant="statusVariant(log.status)" with-dot>
            {{ statusLabel || log.status }}
          </UiBadge>
          <UiBadge variant="default">{{ typeLabel || log.sync_type }}</UiBadge>
          <span class="font-mono text-[11px] text-muted-foreground">#{{ log.id }}</span>
        </div>
      </div>

      <dl class="text-[13px] grid grid-cols-2 gap-x-6 gap-y-2 mb-5">
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('hemis_log.col_target') }}</dt>
          <dd class="font-mono">{{ log.target_id ?? '—' }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('hemis_log.col_attempts') }}</dt>
          <dd class="font-mono">{{ log.attempts }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('hemis_log.f_created') }}</dt>
          <dd class="font-mono text-[11px]">{{ fmt(log.created_at) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('hemis_log.col_completed') }}</dt>
          <dd class="font-mono text-[11px]">{{ fmt(log.completed_at) }}</dd>
        </div>
      </dl>

      <!-- Xato -->
      <template v-if="log.last_error">
        <div class="mono-tag mb-2 text-danger-600">{{ t('hemis_log.f_error') }}</div>
        <pre class="bg-danger-50 dark:bg-danger-700/15 text-danger-700 dark:text-danger-200 text-[11px] font-mono rounded-md p-3 mb-5 whitespace-pre-wrap break-words">{{ log.last_error }}</pre>
      </template>

      <!-- Payload -->
      <div class="mono-tag mb-2">{{ t('hemis_log.f_payload') }}</div>
      <pre
        v-if="pretty(log.payload)"
        class="bg-muted text-foreground text-[11px] font-mono rounded-md p-3 mb-5 overflow-x-auto max-h-64"
      >{{ pretty(log.payload) }}</pre>
      <div v-else class="text-[12px] text-muted-foreground italic mb-5">{{ t('hemis_log.f_no_data') }}</div>

      <!-- Response -->
      <div class="mono-tag mb-2">{{ t('hemis_log.f_response') }}</div>
      <pre
        v-if="pretty(log.response)"
        class="bg-muted text-foreground text-[11px] font-mono rounded-md p-3 overflow-x-auto max-h-64"
      >{{ pretty(log.response) }}</pre>
      <div v-else class="text-[12px] text-muted-foreground italic">{{ t('hemis_log.f_no_data') }}</div>
    </template>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
        <UiButton v-if="log && log.status === 'failed'" @click="emit('retry')">
          {{ t('hemis_log.retry') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
