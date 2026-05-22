<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { rolesApi } from '@shared/api/roles'
import { extractErrorMessage } from '@shared/api/client'
import type { Permission, Role } from '@shared/types/users'

const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const permissionsByCategory = computed(() => {
  const map: Record<string, Permission[]> = {}
  for (const p of permissions.value) {
    const c = p.category ?? 'boshqa'
    map[c] ??= []
    map[c].push(p)
  }
  return map
})

onMounted(async () => {
  loading.value = true
  try {
    const [r, p] = await Promise.all([rolesApi.list(), rolesApi.listPermissions()])
    roles.value = r
    permissions.value = p
  } catch (e) {
    error.value = extractErrorMessage(e, 'Yuklashda xato')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="mb-6">
    <UiBreadcrumb :items="['Admin', 'Boshqaruv', 'Rollar']" class="mb-6" />
      <h1 class="page-title mb-1.5">Rollar va ruxsatlar</h1>
    <p class="page-subtitle">
      Tizimdagi 10 ta rol va ularning permission'lari. Read-only — keyingi phase'da
      universitet darajasida custom rollar yaratish qo'shiladi.
    </p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading" class="text-center py-12 text-muted-foreground">Yuklanmoqda...</div>

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
        <UiBadge v-if="role.is_system" variant="info" with-dot>system</UiBadge>
      </template>
      <p v-if="role.description" class="text-[13px] text-muted-foreground mb-3">
        {{ role.description }}
      </p>
      <div class="mono-tag mb-2">Ruxsatlar ({{ role.permissions.length }})</div>
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

  <UiCard title="Permission katalogi">
    <div class="space-y-4">
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
