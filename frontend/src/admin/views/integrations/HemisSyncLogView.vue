<script setup lang="ts">
/**
 * Phase 8f — HEMIS sync audit log viewer.
 *
 * Admin uchun: barcha HEMIS sync urinishlari (success/failed/pending).
 * Failed yozuvlarni qayta urinish mumkin.
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { hemisApi, type HemisSyncLogItem } from '@shared/api/hemis'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { formatDateTime } from '@shared/utils/datetime'

const { t, locale } = useI18n()

const items = ref<HemisSyncLogItem[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref<string | null>(null)

const typeFilter = ref<string>('')
const statusFilter = ref<string>('')
const page = ref(1)
const pageSize = 50

const stats = ref({ total: 0, success: 0, failed: 0, skipped: 0 })
async function loadStats() {
  const count = (status?: string) =>
    hemisApi.listSyncLog({ status, page: 1, page_size: 1 }).then((r) => r.total).catch(() => 0)
  const [tot, suc, fail, skip] = await Promise.all([
    count(), count('success'), count('failed'), count('skipped'),
  ])
  stats.value = { total: tot, success: suc, failed: fail, skipped: skip }
}

const typeOptions = computed(() => [
  { value: '', label: t('hemis_log.all_types') },
  { value: 'students', label: t('hemis_log.sync_entity_students') },
  { value: 'employees', label: t('hemis_log.sync_entity_employees') },
  { value: 'departments', label: t('hemis_log.sync_entity_departments') },
  { value: 'groups', label: t('hemis_log.sync_entity_groups') },
  { value: 'exam_grades', label: t('hemis_log.type_exam_grades') },
  { value: 'schedule_pull', label: t('hemis_log.type_schedule_pull') },
])

// sync_type / status -> i18n label
const SYNC_TYPE_KEY: Record<string, string> = {
  students: 'sync_entity_students', employees: 'sync_entity_employees',
  departments: 'sync_entity_departments', groups: 'sync_entity_groups',
  exam_grades: 'type_exam_grades', schedule_pull: 'type_schedule_pull',
}
function syncTypeLabel(v: string): string {
  return SYNC_TYPE_KEY[v] ? t(`hemis_log.${SYNC_TYPE_KEY[v]}`) : v
}
const KNOWN_STATUS = ['pending', 'retrying', 'success', 'failed', 'skipped']
function statusLabel(s: string): string {
  return KNOWN_STATUS.includes(s) ? t(`hemis_log.status_${s}`) : s
}

const statusOptions = computed(() => [
  { value: '', label: t('hemis_log.all_statuses') },
  { value: 'pending', label: t('hemis_log.status_pending') },
  { value: 'retrying', label: t('hemis_log.status_retrying') },
  { value: 'success', label: t('hemis_log.status_success') },
  { value: 'failed', label: t('hemis_log.status_failed') },
  { value: 'skipped', label: t('hemis_log.status_skipped') },
])

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await hemisApi.listSyncLog({
      sync_type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
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

watch([typeFilter, statusFilter], () => {
  page.value = 1
  void load()
})
watch(page, load)
onMounted(() => {
  void loadStats()
  void load()
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function statusVariant(s: string): 'default' | 'success' | 'warning' | 'danger' {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'retrying' || s === 'pending') return 'warning'
  return 'default'
}

function fmtDateTime(s: string | null): string {
  if (!s) return '—'
  try {
    return formatDateTime(s, locale.value)
  } catch {
    return s
  }
}

async function retry(item: HemisSyncLogItem) {
  const ok = await confirm({
    title: t('hemis_log.retry_confirm'),
    description: `#${item.id} ${item.sync_type}`,
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    const res = await hemisApi.retry(item.id)
    toast.success(res.status ?? t('common.saved'))
    await load()
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.save_error')))
  }
}

// Phase 10f — manual sync triggers
const syncing = ref<string | null>(null)
async function triggerSync(entity: 'students' | 'employees' | 'departments' | 'groups' | 'all') {
  syncing.value = entity
  try {
    const result = await hemisApi.runSync(entity)
    if (result.status === 'success') {
      toast.success(
        t('hemis_log.sync_success', {
          n: result.upserted,
          entity: t(`hemis_log.sync_entity_${entity}`),
        }),
      )
    } else if (result.status === 'skipped') {
      toast.warning(t('hemis_log.sync_skipped'))
    } else {
      toast.error(t('hemis_log.sync_failed', { error: result.last_error ?? '' }))
    }
    await load()
    await loadStats()
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.save_error')))
  } finally {
    syncing.value = null
  }
}
</script>

<template>
  <UiBreadcrumb :items="['Admin', t('admin_nav.ops'), t('hemis_log.title')]" class="mb-6" />
  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('hemis_log.title') }}</h1>
    <p class="page-subtitle">{{ t('hemis_log.subtitle') }}</p>
  </div>

  <!-- KPI -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
    <UiStatCard :label="t('hemis_log.kpi_total')" :value="String(stats.total)" />
    <UiStatCard :label="t('hemis_log.status_success')" :value="String(stats.success)" tone="success" />
    <UiStatCard :label="t('hemis_log.status_failed')" :value="String(stats.failed)" :tone="stats.failed > 0 ? 'danger' : 'default'" />
    <UiStatCard :label="t('hemis_log.status_skipped')" :value="String(stats.skipped)" />
  </div>

  <!-- Phase 10f — manual sync trigger panel -->
  <UiCard class="mb-4" no-padding>
    <div class="p-4">
      <div class="mb-3 flex items-center justify-between gap-2 flex-wrap">
        <div>
          <div class="text-[13px] font-semibold">{{ t('hemis_log.sync_panel_title') }}</div>
          <div class="text-[11px] text-muted-foreground mt-0.5">
            {{ t('hemis_log.sync_panel_hint') }}
          </div>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton
          variant="primary"
          size="sm"
          :loading="syncing === 'all'"
          :disabled="syncing !== null"
          @click="triggerSync('all')"
        >
          {{ t('hemis_log.sync_all') }}
        </UiButton>
        <UiButton
          variant="outline"
          size="sm"
          :loading="syncing === 'departments'"
          :disabled="syncing !== null"
          @click="triggerSync('departments')"
        >
          {{ t('hemis_log.sync_entity_departments') }}
        </UiButton>
        <UiButton
          variant="outline"
          size="sm"
          :loading="syncing === 'groups'"
          :disabled="syncing !== null"
          @click="triggerSync('groups')"
        >
          {{ t('hemis_log.sync_entity_groups') }}
        </UiButton>
        <UiButton
          variant="outline"
          size="sm"
          :loading="syncing === 'students'"
          :disabled="syncing !== null"
          @click="triggerSync('students')"
        >
          {{ t('hemis_log.sync_entity_students') }}
        </UiButton>
        <UiButton
          variant="outline"
          size="sm"
          :loading="syncing === 'employees'"
          :disabled="syncing !== null"
          @click="triggerSync('employees')"
        >
          {{ t('hemis_log.sync_entity_employees') }}
        </UiButton>
      </div>
    </div>
  </UiCard>

  <UiCard class="mb-4" no-padding>
    <div class="grid grid-cols-1 md:grid-cols-[1fr_1fr] gap-3 p-4">
      <UiSelect v-model="typeFilter" :options="typeOptions" />
      <UiSelect v-model="statusFilter" :options="statusOptions" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && items.length === 0">
    <UiSkeleton :count="6" height="h-16" />
  </div>

  <UiEmptyState
    v-else-if="items.length === 0"
    :title="t('hemis_log.empty')"
    :description="t('hemis_log.empty_hint')"
  />

  <UiCard v-else no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 mono-tag">ID</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('hemis_log.col_type') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('hemis_log.col_target') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('hemis_log.col_status') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('hemis_log.col_attempts') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('hemis_log.col_completed') }}</th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="it in items" :key="it.id" class="hover:bg-muted/40 align-top">
            <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">#{{ it.id }}</td>
            <td class="px-4 py-3 text-[12px]">{{ syncTypeLabel(it.sync_type) }}</td>
            <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
              {{ it.target_id ?? '—' }}
            </td>
            <td class="px-4 py-3">
              <UiBadge :variant="statusVariant(it.status)" with-dot>{{ statusLabel(it.status) }}</UiBadge>
              <div
                v-if="it.last_error"
                class="text-[11px] text-danger-600 mt-1 font-mono truncate max-w-xs"
                :title="it.last_error"
              >
                {{ it.last_error }}
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-[12px] tabular-nums">{{ it.attempts }}</td>
            <td class="px-4 py-3 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
              {{ fmtDateTime(it.completed_at) }}
            </td>
            <td class="px-4 py-3 text-right">
              <UiButton
                v-if="it.status === 'failed'"
                variant="outline"
                size="sm"
                @click="retry(it)"
              >
                {{ t('hemis_log.retry') }}
              </UiButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      class="flex items-center justify-between px-4 py-3 border-t border-border text-[12px] text-muted-foreground"
    >
      <div>
        {{ t('common.total') }}:
        <span class="font-mono text-foreground">{{ total }}</span>
        · {{ t('common.page') }}
        <span class="font-mono text-foreground">{{ page }}</span> /
        <span class="font-mono">{{ totalPages }}</span>
      </div>
      <div class="flex gap-2">
        <UiButton variant="outline" size="sm" :disabled="page <= 1" @click="page--">
          ← {{ t('common.prev') }}
        </UiButton>
        <UiButton variant="outline" size="sm" :disabled="page >= totalPages" @click="page++">
          {{ t('common.next') }} →
        </UiButton>
      </div>
    </div>
  </UiCard>
</template>
