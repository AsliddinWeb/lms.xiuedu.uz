<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { extractErrorMessage } from '@shared/api/client'
import { facultiesApi } from '@shared/api/academic'
import { usersApi } from '@shared/api/users'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { Faculty } from '@shared/types/academic'
import type { UserListItem } from '@shared/types/users'

import FacultyDrawer from '@admin/components/academic/FacultyDrawer.vue'

const { t } = useI18n()

const items = ref<Faculty[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

// Dekan nomlarini ko'rsatish uchun foydalanuvchilar (id -> nom)
const users = ref<UserListItem[]>([])
const deanNameById = computed(() => {
  const m = new Map<number, string>()
  for (const u of users.value) m.set(u.id, u.full_name)
  return m
})
function deanName(id: number | null): string {
  return id != null ? (deanNameById.value.get(id) ?? '—') : '—'
}

const q = ref('')
const page = ref(1)
const pageSize = 50

const drawerOpen = ref(false)
const editing = ref<Faculty | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await facultiesApi.list({
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

let qTimer: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(qTimer)
  qTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 300)
})

watch(page, load)

onMounted(() => {
  void load()
  // Dekan nomzodlari + nomlarini ko'rsatish uchun (xato yutiladi)
  usersApi
    .list({ page: 1, page_size: 200 })
    .then((r) => (users.value = r.items))
    .catch(() => {})
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}
function openEdit(f: Faculty) {
  editing.value = f
  drawerOpen.value = true
}
async function handleDelete(f: Faculty) {
  const ok = await confirm({
    title: t('admin_academic.faculties_delete'),
    description: f.name,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await facultiesApi.remove(f.id)
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
      <UiBreadcrumb :items="['Admin', t('admin_academic.section_label'), t('admin_nav.faculties')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_nav.faculties') }}</h1>
      <p class="page-subtitle">{{ t('admin_academic.faculties_subtitle') }}</p>
    </div>
    <UiButton v-permission="'faculty.manage'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      {{ t('admin_academic.faculties_new') }}
    </UiButton>
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="p-4">
      <UiInput v-model="q" type="search" :placeholder="t('common.search')" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <caption class="sr-only">{{ t('admin_academic.faculties_table_caption') }}</caption>
        <thead>
          <tr class="border-b border-border bg-muted/50">
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_code') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_faculty') }}</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">{{ t('admin_academic.col_dean') }}</th>
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
          <tr v-for="f in items" :key="f.id" class="hover:bg-muted/40">
            <td class="px-4 py-3 font-mono text-[12px]">{{ f.code }}</td>
            <td class="px-4 py-3">
              <div class="font-medium">{{ f.name }}</div>
              <div v-if="f.short_name" class="text-[11px] text-muted-foreground">
                {{ f.short_name }}
              </div>
            </td>
            <td class="px-4 py-3 text-[13px]" :class="f.dean_id == null ? 'text-muted-foreground' : ''">
              {{ deanName(f.dean_id) }}
            </td>
            <td class="px-4 py-3">
              <UiBadge :variant="f.is_active ? 'success' : 'default'" with-dot>
                {{ f.is_active ? t('common.active') : t('common.inactive') }}
              </UiBadge>
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <UiButton v-permission="'faculty.manage'" variant="outline" size="sm"
                class="mr-1" @click="openEdit(f)">{{ t('common.edit') }}</UiButton>
              <UiButton v-permission="'faculty.manage'" variant="ghost" size="sm"
                class="text-danger-600" @click="handleDelete(f)">{{ t('common.delete') }}</UiButton>
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

  <FacultyDrawer
    :open="drawerOpen"
    :faculty="editing"
    :users="users"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
