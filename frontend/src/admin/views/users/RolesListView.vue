<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { rolesApi } from '@shared/api/roles'
import { extractErrorMessage } from '@shared/api/client'
import type { Permission, Role } from '@shared/types/users'

const { t } = useI18n()

const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const search = ref('')

// Qidiruvga mos permissionlar (kod yoki nom bo'yicha)
const filteredPermissions = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return permissions.value
  return permissions.value.filter(
    (p) => p.code.toLowerCase().includes(q) || p.name.toLowerCase().includes(q),
  )
})

const permissionsByCategory = computed(() => {
  const map: Record<string, Permission[]> = {}
  for (const p of filteredPermissions.value) {
    const c = p.category ?? 'boshqa'
    map[c] ??= []
    map[c].push(p)
  }
  return map
})

const hasResults = computed(() => filteredPermissions.value.length > 0)

onMounted(async () => {
  loading.value = true
  try {
    const [r, p] = await Promise.all([rolesApi.list(), rolesApi.listPermissions()])
    roles.value = r
    permissions.value = p
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin_roles.load_error'))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="mb-6">
    <UiBreadcrumb :items="['Admin', t('admin_nav.management'), t('admin_nav.roles')]" class="mb-6" />
    <h1 class="page-title mb-1.5">{{ t('admin_roles.title') }}</h1>
    <p class="page-subtitle">{{ t('admin_roles.subtitle', { n: roles.length }) }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading" class="text-center py-12 text-muted-foreground">{{ t('admin_roles.loading') }}</div>

  <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
    <UiCard
      v-for="role in roles"
      :key="role.id"
      :title="role.name"
    >
      <template #header>
        <div>
          <UiBadge variant="default" class="mb-1">{{ role.code }}</UiBadge>
          <h3 class="text-sm font-semibold text-foreground">{{ role.name }}</h3>
        </div>
        <UiBadge v-if="role.is_system" variant="info" with-dot>{{ t('admin_roles.system') }}</UiBadge>
      </template>
      <p v-if="role.description" class="text-[13px] text-muted-foreground mb-3">
        {{ role.description }}
      </p>
      <div class="mono-tag mb-2">{{ t('admin_roles.perms') }} ({{ role.permissions.length }})</div>
      <div class="flex flex-wrap gap-1">
        <UiBadge v-for="p in role.permissions" :key="p.id" variant="default">
          {{ p.code }}
        </UiBadge>
        <span
          v-if="role.permissions.length === 0"
          class="text-[12px] text-muted-foreground italic"
        >
          —
        </span>
      </div>
    </UiCard>
  </div>

  <UiCard :title="t('admin_roles.catalog_title')">
    <template #actions>
      <UiInput
        v-model="search"
        type="search"
        :placeholder="t('admin_roles.search_placeholder')"
        class="w-full sm:w-72"
      />
    </template>
    <div v-if="!hasResults" class="text-center py-8 text-[13px] text-muted-foreground">
      {{ t('admin_roles.no_results') }}
    </div>
    <div v-else class="space-y-4">
      <div v-for="(perms, cat) in permissionsByCategory" :key="cat">
        <div class="mono-tag mb-2">{{ cat }}</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          <div
            v-for="p in perms"
            :key="p.id"
            class="border border-border rounded p-2.5"
          >
            <div class="font-mono text-[12px] text-foreground">{{ p.code }}</div>
            <div class="text-[12px] text-muted-foreground mt-0.5">{{ p.name }}</div>
          </div>
        </div>
      </div>
    </div>
  </UiCard>
</template>
