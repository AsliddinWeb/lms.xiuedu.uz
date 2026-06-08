<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
import { assignmentsApi } from '@shared/api/assignments'
import { certificatesApi } from '@shared/api/certificates'
import { chatApi } from '@shared/api/chat'
import { useChatSocket } from '@user/composables/useChatSocket'
import { coursesApi, enrollmentsApi } from '@shared/api/courses'
import { examsApi } from '@shared/api/exams'
import { gamificationApi } from '@shared/api/gamification'
import { liveSessionsApi } from '@shared/api/live'
import { useSidebar } from '@shared/composables/useSidebar'
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

// Phase 17.1 — sidebar uchun counts (sanaladigan linklar)
const counts = ref({
  courses: 0,
  assignments: 0,
  exams: 0,
  live: 0,
  certificates: 0,
  badges: 0,
  chatUnread: 0,
  students: 0,
})

async function loadSidebarCounts() {
  if (!auth.user) return
  const tasks: Promise<unknown>[] = []
  if (isStudent.value) {
    tasks.push(
      coursesApi
        .list({ enrolled_user_id: auth.user.id, page_size: 1 })
        .then((r) => (counts.value.courses = r.total))
        .catch(() => undefined),
      assignmentsApi
        .list({ mine: true, is_published: true, only_active: true, page_size: 1 })
        .then((r) => (counts.value.assignments = r.total))
        .catch(() => undefined),
      examsApi
        .my({ page_size: 1 })
        .then((r) => (counts.value.exams = r.total))
        .catch(() => undefined),
      certificatesApi
        .listMine()
        .then((r) => (counts.value.certificates = r.length))
        .catch(() => undefined),
      gamificationApi
        .myStats()
        .then((r) => (counts.value.badges = r.badges_count))
        .catch(() => undefined),
      refreshChatUnread(),
    )
    if (auth.hasPermission('live.join')) {
      tasks.push(
        liveSessionsApi
          .list({ status: 'scheduled', page_size: 1 })
          .then((r) => (counts.value.live = r.total))
          .catch(() => undefined),
      )
    }
  } else {
    // Pedagog
    tasks.push(
      coursesApi
        .list({ primary_author_id: auth.user.id, page_size: 1 })
        .then((r) => (counts.value.courses = r.total))
        .catch(() => undefined),
      assignmentsApi
        .inbox({ status: 'submitted', page_size: 1 })
        .then((r) => (counts.value.assignments = r.total))
        .catch(() => undefined),
    )
    if (auth.hasPermission('live.host')) {
      tasks.push(
        liveSessionsApi
          .list({
            host_user_id: auth.user.id,
            status: 'scheduled',
            page_size: 1,
          })
          .then((r) => (counts.value.live = r.total))
          .catch(() => undefined),
      )
    }
    if (auth.hasPermission('enrollment.read')) {
      tasks.push(
        enrollmentsApi
          .myStudents({ page_size: 1 })
          .then((r) => (counts.value.students = r.total))
          .catch(() => undefined),
      )
    }
  }
  await Promise.all(tasks)
}

// Chat o'qilmaganlar sonini serverdan qayta hisoblaydi (live yangilanish uchun)
async function refreshChatUnread() {
  try {
    const r = await chatApi.listConversations({ page_size: 100 })
    counts.value.chatUnread = r.items.reduce(
      (acc, c) => acc + (c.unread_count ?? 0),
      0,
    )
  } catch {
    // ignore
  }
}

// Real-time: yangi xabar kelganda (WS) yoki suhbat o'qilganda (window event)
// sidebar chat badge'ini jonli yangilaymiz.
const chatWs = useChatSocket()
let chatRefreshTimer: number | null = null
function scheduleChatRefresh() {
  if (chatRefreshTimer !== null) window.clearTimeout(chatRefreshTimer)
  chatRefreshTimer = window.setTimeout(refreshChatUnread, 400)
}
function onChatRead() {
  scheduleChatRefresh()
}

onMounted(() => {
  loadSidebarCounts()
  chatWs.connect()
  chatWs.on((ev) => {
    if (ev.type === 'message.new' || ev.type === 'conversation.read') {
      scheduleChatRefresh()
    }
  })
  window.addEventListener('lms:chat-read', onChatRead)
})

onBeforeUnmount(() => {
  window.removeEventListener('lms:chat-read', onChatRead)
  if (chatRefreshTimer !== null) window.clearTimeout(chatRefreshTimer)
})

/**
 * Talaba (wireframe 04): ASOSIY + BOSHQA + footer
 * Pedagog (wireframe 12): O'QITUVCHI + TAHLIL + footer
 *
 * Disabled (Ph.N badge) — kelajak fazalar uchun placeholder.
 * Profile + Security + Logout — topbar dropdown'ida.
 */
// Count'ni label ichiga inline qo'shadi: "Kurslar (12)"
function withCount(label: string, n: number): string {
  if (n > 0) return `${label} (${n})`
  return label
}

const sections = computed<SidebarSection[]>(() => {
  if (isStudent.value) {
    const main: SidebarNavItem[] = [
      { name: 'dashboard', icon: 'dashboard', label: t('nav.dashboard'), to: '/app/dashboard' },
      {
        name: 'my-learning',
        icon: 'courses',
        label: withCount(t('nav.courses_student'), counts.value.courses),
        to: '/app/learning',
        match: ['/app/course', '/app/forum'],
      },
      {
        name: 'course-catalog',
        icon: 'courses',
        label: t('nav.catalog'),
        to: '/app/catalog',
      },
      {
        name: 'assignments',
        icon: 'assignments',
        label: withCount(t('nav.assignments'), counts.value.assignments),
        to: '/app/assignments',
      },
    ]
    if (auth.hasPermission('exam.attempt')) {
      main.push({
        name: 'my-exams',
        icon: 'exams',
        label: withCount(t('nav.exams'), counts.value.exams),
        to: '/app/exams',
      })
    }
    if (auth.hasPermission('live.join')) {
      main.push({
        name: 'live-upcoming',
        icon: 'live',
        label: withCount(t('nav.live_upcoming'), counts.value.live),
        to: '/app/live/upcoming',
      })
    }
    main.push(
      {
        name: 'schedule',
        icon: 'schedule',
        label: t('nav.schedule'),
        to: '/app/schedule',
      },
      { name: 'grades', icon: 'grades', label: t('nav.grades'), to: '/app/grades' },
    )

    const other: SidebarNavItem[] = [
      {
        name: 'chat',
        icon: 'messages',
        label: withCount(t('nav.chat'), counts.value.chatUnread),
        to: '/app/chat',
      },
      {
        name: 'certificates',
        icon: 'certificates',
        label: withCount(t('nav.certificates'), counts.value.certificates),
        to: '/app/certificates',
      },
      {
        name: 'achievements',
        icon: 'achievements',
        label: withCount(t('nav.achievements'), counts.value.badges),
        to: '/app/achievements',
      },
    ]

    return [
      { title: t('nav.main_section'), items: main },
      { title: t('nav.other_section'), items: other },
    ]
  }

  // Pedagog
  const main: SidebarNavItem[] = [
    { name: 'dashboard', icon: 'dashboard', label: t('nav.dashboard'), to: '/app/dashboard' },
    {
      name: 'courses',
      icon: 'courses',
      label: withCount(t('nav.courses'), counts.value.courses),
      to: '/app/courses',
    },
    {
      name: 'grading',
      icon: 'assignments',
      label: withCount(t('nav.assignments'), counts.value.assignments),
      to: '/app/grading',
    },
  ]
  if (auth.hasPermission('live.host')) {
    main.push({
      name: 'live-host',
      icon: 'live',
      label: withCount(t('nav.live_host'), counts.value.live),
      to: '/app/live',
    })
  }
  main.push({
    name: 'students',
    icon: 'students',
    label: withCount(t('nav.students'), counts.value.students),
    to: '/app/students',
  })

  const analytics: SidebarNavItem[] = [
    { name: 'statistics', icon: 'analytics', label: t('nav.statistics'), disabled: true },
    { name: 'reports', icon: 'audit', label: t('nav.reports'), disabled: true },
  ]

  return [
    { title: t('nav.teacher_section'), items: main },
    { title: t('nav.analytics_section'), items: analytics },
  ]
})

// Footer section: Yordam / Sozlamalar (ikkalasi ham faol)
const footerSection = computed<SidebarSection>(() => ({
  title: '',
  items: [
    { name: 'help', icon: 'help', label: t('nav.help'), to: '/app/help' },
    { name: 'settings', icon: 'settings', label: t('nav.settings'), to: '/app/settings' },
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

// Phase 17 — sidebar holati composable orqali (collapsed + mobile drawer)
const { collapsed: sidebarCollapsed } = useSidebar()
</script>

<template>
  <a href="#main-content" class="skip-link">{{ t('a11y.skip_to_main') }}</a>
  <div
    class="min-h-screen bg-[var(--wireframe-bg)] lg:grid transition-[grid-template-columns] duration-200"
    :style="{ gridTemplateColumns: sidebarCollapsed ? '64px 1fr' : '260px 1fr' }"
  >
    <!-- Sidebar — collapse/expand (desktop), drawer (mobile) -->
    <UiSidebar
      :sections="sections"
      :footer-section="footerSection"
      logo-text="XIU EduPlatform"
      logo-icon="L"
      :logo-to="{ name: 'dashboard' }"
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
