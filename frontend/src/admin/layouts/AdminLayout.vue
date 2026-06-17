<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiLocaleToggle from '@shared/components/ui/UiLocaleToggle.vue'
import UiNotificationBell from '@shared/components/ui/UiNotificationBell.vue'
import UiThemeToggle from '@shared/components/ui/UiThemeToggle.vue'
import UiUserMenu, { type UserMenuItem } from '@shared/components/ui/UiUserMenu.vue'
import UiSidebar, {
  type SidebarNavItem,
  type SidebarSection,
} from '@shared/components/layout/UiSidebar.vue'
import UiTopbar from '@shared/components/layout/UiTopbar.vue'
import { useSidebar } from '@shared/composables/useSidebar'
import { useAuthStore } from '@shared/stores/auth'
import { usersApi } from '@shared/api/users'
import {
  calendarsApi,
  curriculaApi,
  departmentsApi,
  facultiesApi,
  specialtiesApi,
  subjectsApi,
} from '@shared/api/academic'
import { contentApi } from '@shared/api/content'
import { coursesApi } from '@shared/api/courses'
import { liveSessionsApi } from '@shared/api/live'
import { rolesApi } from '@shared/api/roles'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

// Sidebar uchun sanaladigan elementlar soni (badge sifatida ko'rsatiladi)
const counts = ref<Record<string, number>>({})

onMounted(async () => {
  const tasks: Array<[string, Promise<number>]> = [
    ['users', usersApi.list({ page: 1, page_size: 1 }).then((r) => r.total)],
    ['roles', rolesApi.list().then((r) => r.length)],
    ['faculties', facultiesApi.list({ page_size: 1 }).then((r) => r.total)],
    ['departments', departmentsApi.list({ page_size: 1 }).then((r) => r.total)],
    ['specialties', specialtiesApi.list({ page_size: 1 }).then((r) => r.total)],
    ['subjects', subjectsApi.list({ page_size: 1 }).then((r) => r.total)],
    ['curricula', curriculaApi.list({ page_size: 1 }).then((r) => r.total)],
    ['calendars', calendarsApi.list().then((r) => r.length)],
    ['courses', coursesApi.list({ page: 1, page_size: 1 }).then((r) => r.total)],
    ['content', contentApi.list({ page_size: 1 }).then((r) => r.total)],
    ['live', liveSessionsApi.list({ page_size: 1 }).then((r) => r.total)],
  ]
  const results = await Promise.allSettled(tasks.map(([, p]) => p))
  const next: Record<string, number> = {}
  results.forEach((res, i) => {
    if (res.status === 'fulfilled') next[tasks[i][0]] = res.value
  })
  counts.value = next
})

const initials = computed(() => {
  const n = auth.user?.full_name ?? ''
  return (
    n
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? '')
      .join('') || 'A'
  )
})

const sections = computed<SidebarSection[]>(() => {
  const overview: SidebarNavItem[] = [
    { name: 'admin-dashboard', icon: 'dashboard', label: t('admin_nav.dashboard'), to: '/dashboard' },
    { name: 'admin-analytics', icon: 'analytics', label: t('admin_nav.analytics'), to: '/analytics' },
  ]

  // Boshqaruv — kirish/tashkilot
  const management: SidebarNavItem[] = [
    { name: 'admin-users', icon: 'users', label: t('admin_nav.users'), to: '/users', badge: counts.value.users },
    { name: 'admin-roles', icon: 'roles', label: t('admin_nav.roles'), to: '/roles', badge: counts.value.roles },
    { name: 'admin-university', icon: 'university', label: t('admin_nav.university'), to: '/university' },
  ]

  // Akademik tuzilma (breadcrumb'lar bilan izchil — admin_academic.section_label)
  const academic: SidebarNavItem[] = [
    { name: 'admin-faculties', icon: 'faculties', label: t('admin_nav.faculties'), to: '/faculties', badge: counts.value.faculties },
    { name: 'admin-departments', icon: 'departments', label: t('admin_nav.departments'), to: '/departments', badge: counts.value.departments },
    { name: 'admin-specialties', icon: 'specialties', label: t('admin_nav.specialties'), to: '/specialties', badge: counts.value.specialties },
    { name: 'admin-subjects', icon: 'subjects', label: t('admin_nav.subjects'), to: '/subjects', badge: counts.value.subjects },
    { name: 'admin-curricula', icon: 'curricula', label: t('admin_nav.curricula'), to: '/curricula', badge: counts.value.curricula },
    { name: 'admin-calendars', icon: 'calendars', label: t('admin_nav.calendars'), to: '/calendars', badge: counts.value.calendars },
  ]

  const learning: SidebarNavItem[] = [
    { name: 'admin-courses', icon: 'courses', label: t('admin_nav.courses'), to: '/courses', badge: counts.value.courses },
    { name: 'admin-content', icon: 'content', label: t('admin_nav.content'), to: '/content', badge: counts.value.content },
    { name: 'admin-live', icon: 'live', label: t('admin_nav.live'), to: '/live', badge: counts.value.live },
  ]

  return [
    { title: t('admin_nav.overview'), items: overview },
    { title: t('admin_nav.management'), items: management },
    { title: t('admin_academic.section_label'), items: academic },
    { title: t('admin_nav.learning_section'), items: learning },
  ]
})

const footerSection = computed<SidebarSection>(() => ({
  title: t('admin_nav.ops'),
  items: [
    { name: 'admin-reports', icon: 'reports', label: t('admin_nav.reports'), to: '/reports' },
    { name: 'admin-hemis-sync', icon: 'audit', label: t('admin_nav.hemis_sync'), to: '/hemis-sync' },
    { name: 'admin-settings', icon: 'settings', label: t('admin_nav.settings'), to: '/settings' },
  ],
}))

const userMenuItems = computed<UserMenuItem[]>(() => [
  { name: 'logout', icon: 'logout', label: t('admin_nav.logout'), danger: true },
])

async function onUserMenuSelect(item: UserMenuItem) {
  if (item.name === 'logout') {
    await auth.logout()
    router.push({ name: 'admin-login' })
  }
}

// Phase 17 — sidebar holati composable orqali
const { collapsed: sidebarCollapsed } = useSidebar()
</script>

<template>
  <a href="#main-content" class="skip-link">{{ t('a11y.skip_to_main') }}</a>
  <div
    class="min-h-screen bg-[var(--wireframe-bg)] lg:grid transition-[grid-template-columns] duration-200"
    :style="{ gridTemplateColumns: sidebarCollapsed ? '64px 1fr' : '260px 1fr' }"
  >
    <UiSidebar
      :sections="sections"
      :footer-section="footerSection"
      logo-text="Admin Console"
      logo-icon="A"
      :logo-to="{ name: 'admin-dashboard' }"
    />

    <div class="flex flex-col min-h-screen">
      <UiTopbar
        :search-placeholder="t('admin_nav.search_placeholder')"
        :user-name="auth.user?.full_name ?? ''"
        user-role="SUPER ADMIN"
        :initials="initials"
        avatar-color="destructive"
      >
        <template #actions>
          <UiLocaleToggle />
          <UiThemeToggle />
          <UiNotificationBell />
        </template>

        <template #user-menu>
          <UiUserMenu
            :user-name="auth.user?.full_name ?? ''"
            :user-email="auth.user?.email ?? ''"
            user-role="SUPER ADMIN"
            :initials="initials"
            avatar-color="destructive"
            :items="userMenuItems"
            @select="onUserMenuSelect"
          />
        </template>
      </UiTopbar>

      <main
        id="main-content"
        tabindex="-1"
        class="flex-1 p-4 md:p-6 lg:p-8 max-w-[1400px] w-full mx-auto"
      >
        <RouterView />
      </main>
    </div>
  </div>
</template>
