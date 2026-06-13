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
import { departmentsApi } from '@shared/api/academic'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { Department } from '@shared/types/academic'

import DepartmentDrawer from '@admin/components/academic/DepartmentDrawer.vue'
import { useAcademicStore } from '@admin/stores/academic'

const { t } = useI18n()

const store = useAcademicStore()
const items = ref<Department[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const q = ref('')
const facultyFilter = ref<number | null>(null)
const page = ref(1)
const pageSize = 50

const drawerOpen = ref(false)
const editing = ref<Department | null>(null)

const facOptions = computed(() =>
  store.faculties.map((f) => ({ value: f.id, label: `${f.code} — ${f.name}` })),
)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await departmentsApi.list({
      q: q.value || undefined,
      faculty_id: facultyFilter.value ?? undefined,
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
watch(facultyFilter, () => {
  page.value = 1
  void load()
})
watch(page, load)

onMounted(async () => {
  await store.fetchFaculties()
  await load()
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}
function openEdit(d: Department) {
  editing.value = d
  drawerOpen.value = true
}
async function handleDelete(d: Department) {
  const ok = await confirm({
    title: t('admin_academic.departments_delete'),
    description: d.name,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await departmentsApi.remove(d.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.delete_error')))
  }
}

function facLabel(facId: number) {
  const f = store.findFaculty(facId)
  return f ? f.code : `#${facId}`
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_academic.section_label'), t('admin_nav.departments')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_nav.departments') }}</h1>
      <p class="page-subtitle">{{ t('admin_academic.departments_subtitle') }}</p>
    </div>
    <UiButton v-permission="'department.manage'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('admin_academic.departments_new') }}
    </UiButton>
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="grid grid-cols-1 md:grid-cols-[1fr_280px] gap-3 p-4">
      <UiInput v-model="q" type="search" :placeholder="t('common.search')" />
      <UiSelect v-model="facultyFilter" :options="facOptions" :placeholder="t('common.all')" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="border-b border-border bg-muted/50">
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_code') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_department') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_faculty') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_status') }}</th>
            <th scope="col" class="px-4 py-3"><span class="sr-only">{{ t('admin_academic.col_actions') }}</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-if="loading && items.length === 0">
            <td colspan="5" class="text-center py-12 text-muted-foreground">{{ t('common.loading') }}</td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="5" class="text-center py-12 text-muted-foreground">{{ t('common.not_found') }}</td>
          </tr>
          <tr v-for="d in items" :key="d.id" class="hover:bg-muted/40">
            <td class="px-4 py-3 font-mono text-[12px]">{{ d.code }}</td>
            <td class="px-4 py-3 font-medium">{{ d.name }}</td>
            <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
              {{ facLabel(d.faculty_id) }}
            </td>
            <td class="px-4 py-3">
              <UiBadge :variant="d.is_active ? 'success' : 'default'" with-dot>
                {{ d.is_active ? t('common.active') : t('common.inactive') }}
              </UiBadge>
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <UiButton v-permission="'department.manage'" variant="outline" size="sm"
                class="mr-1" @click="openEdit(d)">{{ t('common.edit') }}</UiButton>
              <UiButton v-permission="'department.manage'" variant="ghost" size="sm"
                class="text-danger-600" @click="handleDelete(d)">{{ t('common.delete') }}</UiButton>
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

  <DepartmentDrawer
    :open="drawerOpen"
    :department="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
