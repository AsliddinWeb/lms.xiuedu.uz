<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiLocaleToggle from '@shared/components/ui/UiLocaleToggle.vue'
import UiThemeToggle from '@shared/components/ui/UiThemeToggle.vue'
import UiNotificationBell from '@shared/components/ui/UiNotificationBell.vue'
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
      .join('') || '?'
  )
})

const isStudent = computed(() => !auth.hasPermission('course.create'))

/**
 * Talaba (wireframe 04): ASOSIY + BOSHQA + footer
 * Pedagog (wireframe 12): O'QITUVCHI + TAHLIL + footer
 *
 * Disabled (Ph.N badge) — kelajak fazalar uchun placeholder.
 * Profile + Security + Logout — topbar dropdown'ida.
 */
const sections = computed<SidebarSection[]>(() => {
  if (isStudent.value) {
    const main: SidebarNavItem[] = [
      { name: 'dashboard', icon: 'dashboard', label: t('nav.dashboard'), to: '/app/dashboard' },
      { name: 'my-learning', icon: 'courses', label: t('nav.courses_student'), to: '/app/learning' },
      { name: 'assignments', icon: 'assignments', label: t('nav.assignments'), to: '/app/assignments' },
    ]
    if (auth.hasPermission('exam.attempt')) {
      main.push({
        name: 'my-exams',
        icon: 'audit',
        label: t('nav.exams'),
        to: '/app/exams',
      })
    }
    if (auth.hasPermission('live.join')) {
      main.push({
        name: 'live-upcoming',
        icon: 'live',
        label: t('nav.live_upcoming'),
        to: '/app/live/upcoming',
      })
    }
    main.push(
      { name: 'schedule', icon: 'schedule', label: t('nav.schedule'), disabled: true, badge: 'Ph.6' },
      { name: 'grades', icon: 'grades', label: t('nav.grades'), to: '/app/grades' },
    )

    // Phase 13 — payments LMS skopidan tashqarida (559-qaror), olib tashlandi.
    // Communications/sertifikat/yutuqlar real sahifalar:
    const other: SidebarNavItem[] = [
      { name: 'chat', icon: 'messages', label: t('nav.chat'), to: '/app/chat' },
      { name: 'certificates', icon: 'certificates', label: t('nav.certificates'), to: '/app/certificates' },
      { name: 'achievements', icon: 'achievements', label: t('nav.achievements'), to: '/app/achievements' },
    ]

    return [
      { title: t('nav.main_section'), items: main },
      { title: t('nav.other_section'), items: other },
    ]
  }

  // Pedagog
  const main: SidebarNavItem[] = [
    { name: 'dashboard', icon: 'dashboard', label: t('nav.dashboard'), to: '/app/dashboard' },
    { name: 'courses', icon: 'courses', label: t('nav.courses'), to: '/app/courses' },
    { name: 'grading', icon: 'assignments', label: t('nav.assignments'), to: '/app/grading' },
  ]
  if (auth.hasPermission('live.host')) {
    main.push({
      name: 'live-host',
      icon: 'live',
      label: t('nav.live_host'),
      to: '/app/live',
    })
  }
  main.push({
    name: 'students',
    icon: 'students',
    label: t('nav.students'),
    disabled: true,
    badge: 'Ph.6',
  })

  const analytics: SidebarNavItem[] = [
    { name: 'statistics', icon: 'analytics', label: t('nav.statistics'), disabled: true, badge: 'Ph.9' },
    { name: 'reports', icon: 'audit', label: t('nav.reports'), disabled: true, badge: 'Ph.9' },
  ]

  return [
    { title: t('nav.teacher_section'), items: main },
    { title: t('nav.analytics_section'), items: analytics },
  ]
})

// Footer (border-top): Yordam + Sozlamalar (Ph.6 placeholderlar)
const footerSection = computed<SidebarSection>(() => ({
  title: '',
  items: [
    { name: 'help', icon: 'help', label: t('nav.help'), disabled: true, badge: 'Ph.6' },
    { name: 'settings', icon: 'settings', label: t('nav.settings'), disabled: true, badge: 'Ph.6' },
  ],
}))

// Topbar user dropdown items
const userMenuItems = computed<UserMenuItem[]>(() => [
  { name: 'profile', icon: 'profile', label: t('nav.profile'), to: '/app/profile' },
  { name: 'security', icon: 'security', label: t('nav.security'), to: '/app/security' },
  { name: 'logout-divider', icon: '', label: '', divider: true },
  { name: 'logout', icon: 'logout', label: t('nav.logout'), danger: true },
])

async function onUserMenuSelect(item: UserMenuItem) {
  if (item.name === 'logout') {
    await auth.logout()
    router.push({ name: 'login' })
  }
}

// Phase 8d — mobile sidebar drawer state
const mobileSidebarOpen = ref(false)
</script>

<template>
  <a href="#main-content" class="skip-link">{{ t('a11y.skip_to_main') }}</a>
  <div class="min-h-screen bg-[var(--wireframe-bg)] lg:grid lg:grid-cols-[260px_1fr]">
    <!-- Sidebar — desktop static, mobile drawer -->
    <UiSidebar
      :sections="sections"
      :footer-section="footerSection"
      logo-text="XIU EduPlatform"
      logo-icon="L"
      :logo-to="{ name: 'dashboard' }"
      :mobile-open="mobileSidebarOpen"
      @close-mobile="mobileSidebarOpen = false"
    />

    <!-- Main -->
    <div class="flex flex-col min-h-screen">
      <!-- Topbar -->
      <UiTopbar
        :search-placeholder="t('nav.search_placeholder')"
        :user-name="auth.user?.full_name ?? ''"
        :user-role="isStudent ? t('nav.role_student') : 'PEDAGOG'"
        :initials="initials"
        :show-search="!isStudent"
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
            :user-role="isStudent ? t('nav.role_student') : t('nav.role_teacher')"
            :initials="initials"
            :items="userMenuItems"
            @select="onUserMenuSelect"
          />
        </template>
      </UiTopbar>

      <!-- Content -->
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
