<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { extractErrorMessage } from '@shared/api/client'
import { curriculaApi, specialtiesApi } from '@shared/api/academic'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { Curriculum, Specialty } from '@shared/types/academic'

import CurriculumDrawer from '@admin/components/academic/CurriculumDrawer.vue'

const { t } = useI18n()

const items = ref<Curriculum[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const specialties = ref<Specialty[]>([])

const spFilter = ref<number | null>(null)
const page = ref(1)
const pageSize = 50

const drawerOpen = ref(false)
const editing = ref<Curriculum | null>(null)

const spOptions = computed(() =>
  specialties.value.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` })),
)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await curriculaApi.list({
      specialty_id: spFilter.value ?? undefined,
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

watch(spFilter, () => {
  page.value = 1
  void load()
})
watch(page, load)

onMounted(async () => {
  const sp = await specialtiesApi.list({ page_size: 200 })
  specialties.value = sp.items
  await load()
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}
function openEdit(c: Curriculum) {
  editing.value = c
  drawerOpen.value = true
}

async function handleClone(c: Curriculum) {
  const newVersion = window.prompt(t('admin_academic.curricula_clone_version'), `${c.version || 'v'}.next`)
  if (!newVersion) return
  const newDate = window.prompt(t('admin_academic.curricula_clone_date'), c.valid_from)
  if (!newDate) return
  await curriculaApi.clone(c.id, newVersion, newDate)
  await load()
}

async function handleApprove(c: Curriculum) {
  const ok = await confirm({
    title: t('admin_academic.curricula_approve'),
    description: c.name,
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await curriculaApi.approve(c.id)
    await load()
    toast.success(t('common.saved'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.save_error')))
  }
}

async function handleDelete(c: Curriculum) {
  const ok = await confirm({
    title: t('admin_academic.curricula_delete'),
    description: c.name,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await curriculaApi.remove(c.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.delete_error')))
  }
}

function spLabel(spId: number) {
  const s = specialties.value.find((x) => x.id === spId)
  return s ? s.code : `#${spId}`
}
function basedOnLabel(v: string | null): string {
  if (v === 'DTS') return 'DTS'
  if (v === 'professional_standard') return t('admin_academic.based_prof')
  return v ?? '—'
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_academic.section_label'), t('admin_nav.curricula')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_academic.curricula_title') }}</h1>
      <p class="page-subtitle">{{ t('admin_academic.curricula_subtitle') }}</p>
    </div>
    <UiButton v-permission="'curriculum.manage'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('admin_academic.curricula_new') }}
    </UiButton>
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="p-4">
      <UiSelect v-model="spFilter" :options="spOptions" :placeholder="t('common.all')" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_plan') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_specialty') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_version') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_period') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_credits') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_basis') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_approval') }}</th>
            <th scope="col" class="px-4 py-3"><span class="sr-only">{{ t('admin_academic.col_actions') }}</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-if="loading && items.length === 0">
            <td colspan="8" class="text-center py-12 text-muted-foreground">{{ t('common.loading') }}</td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="8" class="text-center py-12 text-muted-foreground">{{ t('common.not_found') }}</td>
          </tr>
          <tr v-for="c in items" :key="c.id" class="hover:bg-muted/40">
            <td class="px-4 py-3">
              <div class="font-medium">{{ c.name }}</div>
              <div class="text-[11px] text-muted-foreground">
                {{ t('admin_academic.curricula_n_subjects', { n: c.subjects.length }) }}
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-[12px]">{{ spLabel(c.specialty_id) }}</td>
            <td class="px-4 py-3 font-mono text-[12px]">{{ c.version || '—' }}</td>
            <td class="px-4 py-3 font-mono text-[11px] text-muted-foreground">
              {{ c.valid_from }}<br />{{ c.valid_until || '—' }}
            </td>
            <td class="px-4 py-3 font-mono text-[12px] tabular-nums">{{ c.total_credits }}</td>
            <td class="px-4 py-3">
              <UiBadge v-if="c.based_on === 'DTS'" variant="info">DTS</UiBadge>
              <UiBadge v-else-if="c.based_on" variant="default">{{ basedOnLabel(c.based_on) }}</UiBadge>
              <span v-else class="text-[11px] text-muted-foreground">—</span>
            </td>
            <td class="px-4 py-3">
              <UiBadge v-if="c.approved_at" variant="success" with-dot>{{ t('admin_academic.curricula_approved') }}</UiBadge>
              <UiBadge v-else variant="warning" with-dot>{{ t('admin_academic.curricula_not_approved') }}</UiBadge>
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <UiButton v-permission="'curriculum.manage'" variant="outline" size="sm"
                class="mr-1" @click="openEdit(c)">{{ t('common.edit') }}</UiButton>
              <UiButton v-permission="'curriculum.manage'" variant="ghost" size="sm"
                class="mr-1" @click="handleClone(c)">{{ t('admin_academic.curricula_clone') }}</UiButton>
              <UiButton
                v-if="!c.approved_at"
                v-permission="'curriculum.manage'"
                variant="ghost"
                size="sm"
                class="mr-1"
                @click="handleApprove(c)"
              >
                {{ t('common.confirm') }}
              </UiButton>
              <UiButton v-permission="'curriculum.manage'" variant="ghost" size="sm"
                class="text-danger-600" @click="handleDelete(c)">{{ t('common.delete') }}</UiButton>
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

  <CurriculumDrawer
    :open="drawerOpen"
    :curriculum="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
