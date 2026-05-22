<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { calendarsApi } from '@shared/api/academic'
import { apiClient, extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { AcademicCalendar } from '@shared/types/academic'

import AcademicCalendarDrawer from '@admin/components/academic/AcademicCalendarDrawer.vue'

const { t } = useI18n()

const items = ref<AcademicCalendar[]>([])
const currentId = ref<number | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const drawerOpen = ref(false)
const editing = ref<AcademicCalendar | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await calendarsApi.list()
    if (items.value.length > 0) {
      // Single-tenant XIU: joriy kalendar bitta universitet uchun
      const cur = await calendarsApi.getCurrent(items.value[0].organization_id)
      currentId.value = cur?.id ?? null
    } else {
      currentId.value = null
    }
  } catch (e) {
    error.value = extractErrorMessage(e, 'Yuklashda xato')
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}
function openEdit(c: AcademicCalendar) {
  editing.value = c
  drawerOpen.value = true
}
async function handleDelete(c: AcademicCalendar) {
  const ok = await confirm({
    title: t('calendar.confirm_delete'),
    description: c.name,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await apiClient.delete(`/academic-calendars/${c.id}`)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

function isCurrent(c: AcademicCalendar) {
  return currentId.value === c.id
}

function fmtRange(s: string, e: string) {
  return `${s} → ${e}`
}
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', 'Akademik', t('calendar.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('calendar.title') }}</h1>
      <p class="page-subtitle">{{ t('calendar.subtitle') }}</p>
    </div>
    <UiButton v-permission="'calendar.manage'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('calendar.new') }}
    </UiButton>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && items.length === 0" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <div v-else-if="items.length === 0" class="text-center py-12 text-muted-foreground">
    {{ t('calendar.no_calendars') }}
  </div>

  <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <UiCard v-for="c in items" :key="c.id">
      <template #header>
        <div>
          <h3 class="text-base font-semibold text-foreground">
            {{ c.academic_year }} · {{ c.name }}
          </h3>
          <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
            {{ fmtRange(c.start_date, c.end_date) }}
          </div>
        </div>
        <div class="flex items-center gap-1.5">
          <UiBadge v-if="isCurrent(c)" variant="success" with-dot>
            {{ t('calendar.current') }}
          </UiBadge>
          <UiBadge :variant="c.is_active ? 'default' : 'warning'" with-dot>
            {{ c.is_active ? t('common.active') : t('common.inactive') }}
          </UiBadge>
        </div>
      </template>

      <!-- Semesters timeline -->
      <div class="mb-4">
        <div class="mono-tag mb-2">
          {{ t('calendar.card_semesters', { n: c.semesters.length }) }}
        </div>
        <div v-if="c.semesters.length === 0" class="text-[12px] text-muted-foreground italic">
          {{ t('calendar.no_semesters') }}
        </div>
        <div v-else class="space-y-1.5">
          <div
            v-for="(s, i) in c.semesters"
            :key="i"
            class="flex items-center gap-2 text-[13px]"
          >
            <span class="font-medium text-foreground">{{ s.name }}</span>
            <span class="font-mono text-[11px] text-muted-foreground">
              {{ s.start_date }} → {{ s.end_date }}
            </span>
          </div>
        </div>
      </div>

      <!-- Holidays -->
      <div>
        <div class="mono-tag mb-2">
          {{ t('calendar.card_holidays', { n: c.holidays.length }) }}
        </div>
        <div v-if="c.holidays.length === 0" class="text-[12px] text-muted-foreground italic">
          {{ t('calendar.no_holidays') }}
        </div>
        <div v-else class="flex flex-wrap gap-1.5">
          <UiBadge v-for="(h, i) in c.holidays" :key="i" variant="default">
            {{ h.name }} · {{ h.date }}{{ h.days && Number(h.days) > 1 ? ` (${h.days})` : '' }}
          </UiBadge>
        </div>
      </div>

      <template #actions>
        <div class="flex gap-1.5">
          <UiButton v-permission="'calendar.manage'" variant="outline" size="sm" @click="openEdit(c)">
            {{ t('common.edit') }}
          </UiButton>
          <UiButton
            v-permission="'calendar.manage'"
            variant="ghost"
            size="sm"
            class="text-danger-600"
            @click="handleDelete(c)"
          >
            {{ t('common.delete') }}
          </UiButton>
        </div>
      </template>
    </UiCard>
  </div>

  <AcademicCalendarDrawer
    :open="drawerOpen"
    :calendar="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
