<script setup lang="ts">
import { computed, ref } from 'vue'
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
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

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
    { name: 'analytics', icon: 'analytics', label: t('admin_nav.analytics'), disabled: true, badge: 'Ph.9' },
  ]

  const management: SidebarNavItem[] = [
    { name: 'admin-users', icon: 'users', label: t('admin_nav.users'), to: '/users' },
    { name: 'admin-roles', icon: 'roles', label: t('admin_nav.roles'), to: '/roles' },
    { name: 'admin-university', icon: 'university', label: t('admin_nav.university'), to: '/university' },
    { name: 'admin-faculties', icon: 'faculties', label: t('admin_nav.faculties'), to: '/faculties' },
    { name: 'admin-departments', icon: 'departments', label: t('admin_nav.departments'), to: '/departments' },
    { name: 'admin-specialties', icon: 'specialties', label: t('admin_nav.specialties'), to: '/specialties' },
    { name: 'admin-subjects', icon: 'subjects', label: t('admin_nav.subjects'), to: '/subjects' },
    { name: 'admin-curricula', icon: 'curricula', label: t('admin_nav.curricula'), to: '/curricula' },
    { name: 'admin-calendars', icon: 'calendars', label: t('admin_nav.calendars'), to: '/calendars' },
  ]

  const learning: SidebarNavItem[] = [
    { name: 'admin-courses', icon: 'courses', label: t('admin_nav.courses'), to: '/courses' },
    { name: 'admin-content', icon: 'content', label: t('admin_nav.content'), to: '/content' },
    { name: 'admin-live', icon: 'live', label: t('admin_nav.live'), to: '/live' },
  ]

  return [
    { title: t('admin_nav.overview'), items: overview },
    { title: t('admin_nav.management'), items: management },
    { title: t('admin_nav.learning_section'), items: learning },
  ]
})

const footerSection = computed<SidebarSection>(() => ({
  title: t('admin_nav.ops'),
  items: [
    { name: 'admin-reports', icon: 'reports', label: t('admin_nav.reports'), to: '/reports' },
    { name: 'admin-hemis-sync', icon: 'audit', label: t('admin_nav.hemis_sync'), to: '/hemis-sync' },
    { name: 'settings', icon: 'settings', label: t('admin_nav.settings'), disabled: true, badge: 'Ph.10' },
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

// Phase 8d — mobile sidebar drawer state
const mobileSidebarOpen = ref(false)
</script>

<template>
  <a href="#main-content" class="skip-link">{{ t('a11y.skip_to_main') }}</a>
  <div class="min-h-screen bg-[var(--wireframe-bg)] lg:grid lg:grid-cols-[260px_1fr]">
    <UiSidebar
      :sections="sections"
      :footer-section="footerSection"
      logo-text="Admin Console"
      logo-icon="A"
      :logo-to="{ name: 'admin-dashboard' }"
      :mobile-open="mobileSidebarOpen"
      @close-mobile="mobileSidebarOpen = false"
    />

    <div class="flex flex-col min-h-screen">
      <UiTopbar
        :search-placeholder="t('admin_nav.search_placeholder')"
        :user-name="auth.user?.full_name ?? ''"
        user-role="SUPER ADMIN"
        :initials="initials"
        avatar-color="destructive"
        @toggle-mobile="mobileSidebarOpen = !mobileSidebarOpen"
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
