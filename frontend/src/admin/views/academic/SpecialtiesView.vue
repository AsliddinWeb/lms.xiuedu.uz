<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { extractErrorMessage } from '@shared/api/client'
import { departmentsApi, specialtiesApi } from '@shared/api/academic'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { Department, Specialty } from '@shared/types/academic'

import SpecialtyDrawer from '@admin/components/academic/SpecialtyDrawer.vue'

const { t } = useI18n()

const items = ref<Specialty[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const departments = ref<Department[]>([])

const q = ref('')
const depFilter = ref<number | null>(null)
const levelFilter = ref<string | null>(null)
const distanceFilter = ref<string | null>(null)
const page = ref(1)
const pageSize = 50

const drawerOpen = ref(false)
const editing = ref<Specialty | null>(null)

const depOptions = computed(() =>
  departments.value.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })),
)
const levelOptions = [
  { value: 'bachelor', label: 'Bakalavr' },
  { value: 'master', label: 'Magistr' },
  { value: 'phd', label: 'PhD' },
]
const distanceOptions = [
  { value: 'true', label: 'Faqat masofaviy' },
  { value: 'false', label: 'Hammasi' },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await specialtiesApi.list({
      q: q.value || undefined,
      department_id: depFilter.value ?? undefined,
      level: levelFilter.value ?? undefined,
      distance_only: distanceFilter.value === 'true' ? true : undefined,
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

let qTimer: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(qTimer)
  qTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 300)
})
watch([depFilter, levelFilter, distanceFilter], () => {
  page.value = 1
  void load()
})

onMounted(async () => {
  const deps = await departmentsApi.list({ page_size: 200 })
  departments.value = deps.items
  await load()
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}
function openEdit(s: Specialty) {
  editing.value = s
  drawerOpen.value = true
}
async function handleEnableDistance(s: Specialty) {
  if (s.distance_enabled) return
  await specialtiesApi.enableDistance(s.id)
  await load()
}
async function handleDelete(s: Specialty) {
  const ok = await confirm({
    title: 'Yo\'nalishni o\'chirish?',
    description: s.name,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await specialtiesApi.remove(s.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.delete_error')))
  }
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_academic.section_label'), t('admin_nav.specialties')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_academic.specialties_title') }}</h1>
      <p class="page-subtitle">{{ t('admin_academic.specialties_subtitle') }}</p>
    </div>
    <UiButton v-permission="'specialty.manage'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('admin_academic.specialties_new') }}
    </UiButton>
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="grid grid-cols-1 md:grid-cols-[1fr_220px_180px_180px] gap-3 p-4">
      <UiInput v-model="q" type="search" :placeholder="t('common.search')" />
      <UiSelect v-model="depFilter" :options="depOptions" :placeholder="t('common.all')" />
      <UiSelect v-model="levelFilter" :options="levelOptions" :placeholder="t('common.all')" />
      <UiSelect v-model="distanceFilter" :options="distanceOptions" :placeholder="t('common.all')" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="border-b border-border bg-muted/50">
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_dts') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_specialty') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_level_duration') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_form_lang') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_quota') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_distance') }}</th>
            <th scope="col" class="px-4 py-3"><span class="sr-only">{{ t('admin_academic.col_actions') }}</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-if="loading && items.length === 0">
            <td colspan="7" class="text-center py-12 text-muted-foreground">{{ t('common.loading') }}</td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="7" class="text-center py-12 text-muted-foreground">{{ t('common.not_found') }}</td>
          </tr>
          <tr v-for="s in items" :key="s.id" class="hover:bg-muted/40">
            <td class="px-4 py-3 font-mono text-[12px]">{{ s.code }}</td>
            <td class="px-4 py-3 font-medium">{{ s.name }}</td>
            <td class="px-4 py-3">
              <UiBadge :variant="s.level === 'bachelor' ? 'info' : 'warning'">
                {{ s.level }}
              </UiBadge>
              <span class="ml-2 font-mono text-[11px] text-muted-foreground">
                {{ s.duration_years }} yil
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="font-mono text-[11px] text-muted-foreground">
                {{ s.education_form }} · {{ s.language }}
              </span>
            </td>
            <td class="px-4 py-3 font-mono text-[12px] tabular-nums">
              {{ s.annual_quota ?? '—' }}
            </td>
            <td class="px-4 py-3">
              <UiBadge v-if="s.distance_enabled" variant="success" with-dot>{{ t('admin_academic.specialties_distance_enabled') }}</UiBadge>
              <UiButton
                v-else
                v-permission="'specialty.manage'"
                variant="outline"
                size="sm"
                @click="handleEnableDistance(s)"
              >
                {{ t('admin_academic.specialties_distance_allow') }}
              </UiButton>
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <UiButton v-permission="'specialty.manage'" variant="outline" size="sm"
                class="mr-1" @click="openEdit(s)">{{ t('common.edit') }}</UiButton>
              <UiButton v-permission="'specialty.manage'" variant="ghost" size="sm"
                class="text-danger-600" @click="handleDelete(s)">{{ t('common.delete') }}</UiButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center justify-between px-4 py-3 border-t border-border text-[12px]
      text-muted-foreground">
      <div>
        {{ t('common.total') }}: <span class="font-mono text-foreground">{{ total }}</span> · {{ t('common.page') }}
        <span class="font-mono text-foreground">{{ page }}</span> /
        <span class="font-mono">{{ totalPages }}</span>
      </div>
      <div class="flex gap-2">
        <UiButton variant="outline" size="sm" :disabled="page <= 1" @click="page--">← {{ t('common.prev') }}</UiButton>
        <UiButton variant="outline" size="sm" :disabled="page >= totalPages" @click="page++">{{ t('common.next') }} →</UiButton>
      </div>
    </div>
  </UiCard>

  <SpecialtyDrawer
    :open="drawerOpen"
    :specialty="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
