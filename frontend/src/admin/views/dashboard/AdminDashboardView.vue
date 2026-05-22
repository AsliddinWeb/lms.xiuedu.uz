<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { coursesApi } from '@shared/api/courses'
import { facultiesApi } from '@shared/api/academic'
import { usersApi } from '@shared/api/users'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const kpiFaculties = ref<number | string>('—')
const kpiUsers = ref<number | string>('—')
const kpiCourses = ref<number | string>('—')
const kpiPublishedCourses = ref<number | string>('—')

async function loadKpis() {
  try {
    const faculties = await facultiesApi.list({ page_size: 1 })
    kpiFaculties.value = faculties.total
  } catch {}

  try {
    const users = await usersApi.list({ page_size: 1 })
    kpiUsers.value = users.total
  } catch {}

  try {
    const all = await coursesApi.list({ page_size: 1 })
    kpiCourses.value = all.total
  } catch {}

  try {
    const pub = await coursesApi.list({ status: 'published', page_size: 1 })
    kpiPublishedCourses.value = pub.total
  } catch {}
}

onMounted(loadKpis)

const components = [
  { name: 'Backend API (FastAPI)', port: '8200' },
  { name: 'PostgreSQL', port: '8210' },
  { name: 'Redis', port: '8211' },
  { name: 'MinIO (S3)', port: '8212/8213' },
  { name: 'Mailhog (dev SMTP)', port: '8214/8215' },
]

const phases = [
  { code: 'P0', label: 'Foundation', status: 'success' as const },
  { code: 'P1', label: 'Auth + RBAC + Users', status: 'success' as const },
  { code: 'P2', label: 'Akademik + Profile + i18n', status: 'success' as const },
  { code: 'P3', label: 'Content + Courses', status: 'success' as const },
  { code: 'P4', label: 'Assignments + Grading', status: 'success' as const },
  { code: 'P5', label: 'Live darslar (WebRTC)', status: 'default' as const },
  { code: 'P6', label: 'Imtihonlar + Proktoring', status: 'default' as const },
  { code: 'P7', label: 'Deploy + monitoring', status: 'default' as const },
]
</script>

<template>
  <UiBreadcrumb
    :items="[t('admin_nav.overview'), t('admin_dashboard.title')]"
    class="mb-6"
  />
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('admin_dashboard.title') }}</h1>
      <p class="page-subtitle">
        {{ t('admin_dashboard.subtitle') }}
        <span v-if="auth.user" class="text-muted-foreground">
          — {{ auth.user.full_name }}
        </span>
      </p>
    </div>
    <UiBadge variant="success" with-dot>
      {{ t('admin_dashboard.system_active') }}
    </UiBadge>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
    <UiStatCard :label="t('admin_dashboard.kpi_faculties')" :value="String(kpiFaculties)" />
    <UiStatCard :label="t('admin_dashboard.kpi_users')" :value="String(kpiUsers)" />
    <UiStatCard :label="t('admin_dashboard.kpi_courses')" :value="String(kpiCourses)" />
    <UiStatCard
      :label="t('admin_dashboard.kpi_published_courses')"
      :value="String(kpiPublishedCourses)"
    />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <!-- Tizim holati (2 col) -->
    <UiCard :title="t('admin_dashboard.system_status')" class="lg:col-span-2">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="text-left">
            <th scope="col" class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider pb-2">
              {{ t('admin_dashboard.col_component') }}
            </th>
            <th scope="col" class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider pb-2">
              {{ t('admin_dashboard.col_status') }}
            </th>
            <th scope="col" class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider pb-2 text-right">
              {{ t('admin_dashboard.col_port') }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="row in components" :key="row.name">
            <td class="py-2.5">{{ row.name }}</td>
            <td class="py-2.5">
              <UiBadge variant="success" with-dot>
                {{ t('admin_dashboard.status_healthy') }}
              </UiBadge>
            </td>
            <td class="py-2.5 text-right font-mono text-[12px] text-muted-foreground">
              {{ row.port }}
            </td>
          </tr>
        </tbody>
      </table>
    </UiCard>

    <UiCard :title="t('admin_dashboard.my_session')">
      <dl class="space-y-2.5 text-[13px] mb-4">
        <div>
          <dt class="mono-tag mb-1">email</dt>
          <dd class="font-mono text-[12px] text-foreground truncate">{{ auth.user?.email }}</dd>
        </div>
        <div>
          <dt class="mono-tag mb-1">{{ t('admin_nav.users') }}</dt>
          <dd class="flex flex-wrap gap-1.5">
            <UiBadge v-for="r in auth.roles" :key="r" variant="info">{{ r }}</UiBadge>
          </dd>
        </div>
      </dl>
      <div>
        <div class="mono-tag mb-2">permissions ({{ auth.permissions.length }})</div>
        <div class="max-h-32 overflow-y-auto flex flex-wrap gap-1">
          <span
            v-for="p in auth.permissions"
            :key="p"
            class="font-mono text-[10px] bg-muted text-muted-foreground rounded px-1.5 py-0.5"
          >
            {{ p }}
          </span>
        </div>
      </div>
    </UiCard>
  </div>

  <div class="mt-6">
    <UiCard :title="t('admin_dashboard.phases_progress')">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <div
          v-for="phase in phases"
          :key="phase.code"
          class="border border-border rounded-md p-3"
        >
          <UiBadge :variant="phase.status" with-dot class="mb-1.5">{{ phase.code }}</UiBadge>
          <div class="text-[12px] text-foreground">{{ phase.label }}</div>
        </div>
      </div>
    </UiCard>
  </div>
</template>
