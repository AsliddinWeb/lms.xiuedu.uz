<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { usersApi } from '@shared/api/users'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { formatDate as fmtDateUtil } from '@shared/utils/datetime'
import type { UserDetail, UserListItem } from '@shared/types/users'

import UserFormDrawer from '@admin/components/UserFormDrawer.vue'
import { useUsersStore } from '@admin/stores/users'

const { locale } = useI18n()
const store = useUsersStore()

const q = ref('')
const roleFilter = ref<string | null>(null)
const statusFilter = ref<string | null>(null) // 'active' | 'inactive' | null
const page = ref(1)
const pageSize = 20

const drawerOpen = ref(false)
const editing = ref<UserDetail | null>(null)

const statusOptions = [
  { value: 'active', label: 'Faol' },
  { value: 'inactive', label: 'Faolsizlangan' },
]

const roleOptions = computed(() =>
  store.roles.map((r) => ({ value: r.code, label: `${r.code} — ${r.name}` })),
)

async function load() {
  await store.fetchList({
    q: q.value || undefined,
    role: roleFilter.value || undefined,
    is_active:
      statusFilter.value === null
        ? undefined
        : statusFilter.value === 'active',
    page: page.value,
    page_size: pageSize,
  })
}

let qDebounce: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(qDebounce)
  qDebounce = setTimeout(() => {
    page.value = 1
    void load()
  }, 300)
})

watch([roleFilter, statusFilter], () => {
  page.value = 1
  void load()
})

watch(page, load)

onMounted(async () => {
  await store.fetchRoles()
  await load()
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(store.list.total / pageSize)),
)

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}

async function openEdit(u: UserListItem) {
  editing.value = await usersApi.get(u.id)
  drawerOpen.value = true
}

async function handleToggleActive(u: UserListItem) {
  try {
    if (u.is_active) await store.deactivate(u.id)
    else await store.activate(u.id)
    await load()
  } catch (e) {
    console.error(e)
  }
}

async function handleDelete(u: UserListItem) {
  const ok = await confirm({
    title: 'Foydalanuvchini o\'chirish (soft-delete)?',
    description: u.email,
    variant: 'danger',
    confirmLabel: 'O\'chirish',
    cancelLabel: 'Bekor',
  })
  if (!ok) return
  try {
    await store.remove(u.id)
    await load()
    toast.success('O\'chirildi')
  } catch (e) {
    toast.error('O\'chirishda xato')
    console.error(e)
  }
}

function formatDate(s: string | null): string {
  if (!s) return '—'
  try {
    return fmtDateUtil(s, locale.value, {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return s
  }
}

// Phase 8f — bulk selection state
const selected = ref<Set<number>>(new Set())
const bulkActing = ref(false)

const allSelected = computed(
  () =>
    store.list.items.length > 0 &&
    store.list.items.every((u) => selected.value.has(u.id)),
)

function toggleOne(id: number) {
  if (selected.value.has(id)) selected.value.delete(id)
  else selected.value.add(id)
}

function toggleAll() {
  if (allSelected.value) {
    selected.value.clear()
  } else {
    for (const u of store.list.items) selected.value.add(u.id)
  }
}

// Sahifa o'zgarganda tanlovni tozalash
watch([page, roleFilter, statusFilter, q], () => {
  selected.value.clear()
})

async function bulkSetActive(active: boolean) {
  if (selected.value.size === 0) return
  const ok = await confirm({
    title: active
      ? `${selected.value.size} ta foydalanuvchini faollashtirish?`
      : `${selected.value.size} ta foydalanuvchini faolsizlantirish?`,
    confirmLabel: 'Tasdiqlash',
    cancelLabel: 'Bekor',
  })
  if (!ok) return
  bulkActing.value = true
  let ok_count = 0
  let fail_count = 0
  for (const id of selected.value) {
    try {
      if (active) await store.activate(id)
      else await store.deactivate(id)
      ok_count++
    } catch {
      fail_count++
    }
  }
  bulkActing.value = false
  selected.value.clear()
  if (fail_count === 0) {
    toast.success(`${ok_count} ta yangilandi`)
  } else {
    toast.warning(`${ok_count} ta yangilandi, ${fail_count} xato`)
  }
  await load()
}
</script>

<template>
  <UiBreadcrumb :items="['Admin', 'Boshqaruv', 'Foydalanuvchilar']" class="mb-6" />
  <!-- Page header -->
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">Foydalanuvchilar</h1>
      <p class="page-subtitle">
        Tizim foydalanuvchilarini boshqarish — yaratish, tahrirlash, rollar biriktirish.
      </p>
    </div>
    <UiButton v-permission="'users.manage'" @click="openCreate">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round">
        <path d="M7 2v10M2 7h10" />
      </svg>
      Yangi foydalanuvchi
    </UiButton>
  </div>

  <!-- Filters -->
  <UiCard class="mb-4" no-padding>
    <div class="grid grid-cols-1 md:grid-cols-[1fr_200px_180px] gap-3 p-4">
      <UiInput v-model="q" type="search" placeholder="Email, ism yoki telefon bo'yicha qidirish..." />
      <UiSelect
        v-model="roleFilter"
        :options="roleOptions"
        placeholder="Hamma rollar"
      />
      <UiSelect
        v-model="statusFilter"
        :options="statusOptions"
        placeholder="Hamma statuslar"
      />
    </div>
  </UiCard>

  <UiAlert v-if="store.error" variant="danger" class="mb-4">{{ store.error }}</UiAlert>

  <!-- Table -->
  <!-- Bulk action toolbar (faqat tanlangan bo'lsa) -->
  <div
    v-if="selected.size > 0"
    class="mb-3 flex items-center gap-2 p-3 bg-muted/40 border border-border rounded-md"
  >
    <span class="text-[13px] font-medium">
      {{ $t('common.selected_n', { n: selected.size }) }}
    </span>
    <div class="ml-auto flex gap-2">
      <UiButton
        v-permission="'users.manage'"
        variant="outline"
        size="sm"
        :loading="bulkActing"
        @click="bulkSetActive(true)"
      >
        Faollashtirish
      </UiButton>
      <UiButton
        v-permission="'users.manage'"
        variant="outline"
        size="sm"
        :loading="bulkActing"
        @click="bulkSetActive(false)"
      >
        Faolsizlantirish
      </UiButton>
      <UiButton variant="ghost" size="sm" @click="selected.clear()">
        ✕
      </UiButton>
    </div>
  </div>

  <UiCard no-padding>
    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="border-b border-border bg-muted/50">
            <th scope="col" class="px-4 py-3 w-10">
              <input
                type="checkbox"
                :checked="allSelected"
                :aria-label="$t('common.select_all')"
                @change="toggleAll"
              />
            </th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">ID</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">Foydalanuvchi</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">Rollar</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">Status</th>
            <th scope="col" class="text-left px-4 py-3 mono-tag">Oxirgi kirish</th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-if="store.loading && store.list.items.length === 0">
            <td colspan="7" class="text-center py-12 text-muted-foreground">Yuklanmoqda...</td>
          </tr>
          <tr v-else-if="store.list.items.length === 0">
            <td colspan="7" class="text-center py-12 text-muted-foreground">
              Hech narsa topilmadi
            </td>
          </tr>
          <tr
            v-for="u in store.list.items"
            :key="u.id"
            class="hover:bg-muted/40 transition"
            :class="selected.has(u.id) ? 'bg-muted/60' : ''"
          >
            <td class="px-4 py-3">
              <input
                type="checkbox"
                :checked="selected.has(u.id)"
                :aria-label="`Select user ${u.email}`"
                @change="toggleOne(u.id)"
              />
            </td>
            <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">#{{ u.id }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-foreground">{{ u.full_name }}</div>
              <div class="font-mono text-[11px] text-muted-foreground">{{ u.email }}</div>
            </td>
            <td class="px-4 py-3">
              <div class="flex flex-wrap gap-1">
                <UiBadge v-for="r in u.roles" :key="r" variant="info">{{ r }}</UiBadge>
                <span v-if="u.roles.length === 0" class="text-[11px] text-muted-foreground italic">
                  rolsiz
                </span>
              </div>
            </td>
            <td class="px-4 py-3">
              <div class="flex flex-col gap-1">
                <UiBadge :variant="u.is_active ? 'success' : 'default'" with-dot>
                  {{ u.is_active ? 'Faol' : 'Faolsiz' }}
                </UiBadge>
                <UiBadge v-if="u.is_verified" variant="success" with-dot>Tasdiqlangan</UiBadge>
                <UiBadge v-if="u.is_2fa_enabled" variant="info" with-dot>2FA</UiBadge>
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
              {{ formatDate(u.last_login_at) }}
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <UiButton
                v-permission="'users.manage'"
                variant="outline"
                size="sm"
                class="mr-1"
                @click="openEdit(u)"
              >
                Tahrir
              </UiButton>
              <UiButton
                v-permission="'users.manage'"
                variant="ghost"
                size="sm"
                class="mr-1"
                @click="handleToggleActive(u)"
              >
                {{ u.is_active ? 'Faolsizlash' : "Faollashtirish" }}
              </UiButton>
              <UiButton
                v-permission="'users.manage'"
                variant="ghost"
                size="sm"
                class="text-danger-600"
                @click="handleDelete(u)"
              >
                O'chirish
              </UiButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      class="flex items-center justify-between px-4 py-3 border-t border-border text-[12px] text-muted-foreground"
    >
      <div>
        Jami: <span class="font-mono text-foreground">{{ store.list.total }}</span> ·
        Sahifa
        <span class="font-mono text-foreground">{{ page }}</span> /
        <span class="font-mono">{{ totalPages }}</span>
      </div>
      <div class="flex items-center gap-2">
        <UiButton
          variant="outline"
          size="sm"
          :disabled="page <= 1 || store.loading"
          @click="page--"
        >
          ← Oldin
        </UiButton>
        <UiButton
          variant="outline"
          size="sm"
          :disabled="page >= totalPages || store.loading"
          @click="page++"
        >
          Keyingi →
        </UiButton>
      </div>
    </div>
  </UiCard>

  <UserFormDrawer
    :open="drawerOpen"
    :user="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
