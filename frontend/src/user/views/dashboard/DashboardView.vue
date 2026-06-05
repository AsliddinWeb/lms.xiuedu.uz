<script setup lang="ts">
/**
 * Talaba/Pedagog dashboard — wireframe 04 (student) / wireframe 12 (teacher) bo'yicha.
 * - Page header: breadcrumb + h1 + subtitle + action buttons
 * - 4-stat grid (yellow tone "Baholash kutmoqda" teacher uchun)
 * - 2-col area: LEFT (Davom etish/Continue + Activity chart) + RIGHT (Jadval + Deadlines + E'lonlar)
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiImagePlaceholder from '@shared/components/ui/UiImagePlaceholder.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import UiChartBar from '@shared/components/ui/UiChartBar.vue'
import { assignmentsApi } from '@shared/api/assignments'
import {
  activityApi,
  coursesApi,
  gradebookApi,
  progressApi,
  type ActivityResponse,
} from '@shared/api/courses'
import { liveSessionsApi } from '@shared/api/live'
import { certificatesApi } from '@shared/api/certificates'
import {
  gamificationApi,
  type MyGamificationStats,
} from '@shared/api/gamification'
import { examsApi } from '@shared/api/exams'
import { notificationsApi, type NotificationPublic } from '@shared/api/notifications'
import { useAuthStore } from '@shared/stores/auth'
import type { Course } from '@shared/types/courses'
import type { Exam } from '@shared/types/exams'
import type { LiveSession } from '@shared/types/live'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const isStudent = computed(() => !auth.hasPermission('course.create'))
const isTeacher = computed(() => auth.hasPermission('course.create'))

// KPIs
const enrolledCount = ref(0)
const myCoursesCount = ref(0)
const studentsCount = ref(0)
const activeAssignmentsCount = ref(0)
const pendingGradingCount = ref(0)
const recentCourses = ref<Course[]>([])
const recentAssignments = ref<{ id: number; title: string; due_date: string; course_id: number | null }[]>([])
const upcomingLive = ref<LiveSession[]>([])
const liveNow = ref<LiveSession[]>([])

// Phase 13 — talaba uchun gamif + sertifikat
const gamifStats = ref<MyGamificationStats | null>(null)
const certificatesCount = ref(0)

// Akademik ko'rsatkich (GPA) — Baholar moduli bilan bir xil hisob
const gpa = ref<number | null>(null)
const gradeAvg = ref<number | null>(null)
const gradedCount = ref(0)

// 4.0 GPA — backend harf bandlariga mos (GradesView bilan bir xil)
function gpaPoints(percent: number): number {
  if (percent >= 86) return 4
  if (percent >= 71) return 3
  if (percent >= 55) return 2
  return 0
}
// Kurs progress map (course_id => percent)
const courseProgress = ref<Record<number, number>>({})

// Phase 16 — real activity chart + period switcher
const activityPeriod = ref<7 | 30 | 365>(7)
const activityData = ref<ActivityResponse | null>(null)

// Phase 16 — yaqin imtihonlar va top notifications
const upcomingExams = ref<Exam[]>([])
const topNotifications = ref<NotificationPublic[]>([])
const unreadNotificationCount = ref(0)

// Activity chart UI ma'lumotlari
const weekActivity = computed(() => {
  const days = activityData.value?.days ?? []
  return days.map((d) => {
    const date = new Date(d.date + 'T00:00:00')
    const label = new Intl.DateTimeFormat(locale.value, {
      weekday: 'short',
    }).format(date)
    return { label, value: d.time_minutes }
  })
})

const totalHours = computed(() => {
  const mins = activityData.value?.total_minutes ?? 0
  return Math.round((mins / 60) * 10) / 10
})

const streakDays = computed(() => activityData.value?.streak_days ?? 0)

const mostActiveLabel = computed(() => {
  const iso = activityData.value?.most_active_label
  if (!iso) return '—'
  try {
    const date = new Date(iso + 'T00:00:00')
    return new Intl.DateTimeFormat(locale.value, {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
    }).format(date)
  } catch {
    return iso
  }
})

async function loadStudentData() {
  if (!auth.user) return
  try {
    const enrolled = await coursesApi.list({
      enrolled_user_id: auth.user.id,
      page_size: 100,
    })
    enrolledCount.value = enrolled.total
    recentCourses.value = enrolled.items.slice(0, 3)

    // Har bir aktiv kurs uchun progress
    const progresses = await Promise.all(
      recentCourses.value.map((c) =>
        progressApi.myCourseProgress(c.id).catch(() => null),
      ),
    )
    const map: Record<number, number> = {}
    progresses.forEach((p, idx) => {
      if (p) {
        const pct = Number(p.percent)
        map[recentCourses.value[idx].id] = Number.isFinite(pct) ? Math.round(pct) : 0
      }
    })
    courseProgress.value = map

    const active = await assignmentsApi.list({
      mine: true,
      is_published: true,
      only_active: true,
      page_size: 5,
    })
    activeAssignmentsCount.value = active.total
    recentAssignments.value = active.items.map((a) => ({
      id: a.id,
      title: a.title,
      due_date: a.due_date,
      course_id: a.course_id ?? null,
    }))

    // Gamification + sertifikatlar + gradebook (parallel, xatosini yutamiz)
    const [gamif, certs, rows] = await Promise.all([
      gamificationApi.myStats().catch(() => null),
      certificatesApi.listMine().catch(() => [] as unknown[]),
      gradebookApi.myGradebook().catch(() => []),
    ])
    gamifStats.value = gamif
    certificatesCount.value = Array.isArray(certs) ? certs.length : 0

    // GPA — faqat baholangan kurslar (grade_number > 0), kreditga vaznli
    const graded = rows.filter(
      (r) => Number.isFinite(r.grade_number) && r.grade_number > 0,
    )
    gradedCount.value = graded.length
    if (graded.length > 0) {
      const cr = graded.reduce((a, r) => a + r.credits, 0) || 1
      const wPct = graded.reduce((a, r) => a + r.grade_number * r.credits, 0) / cr
      const wGpa = graded.reduce((a, r) => a + gpaPoints(r.grade_number) * r.credits, 0) / cr
      gradeAvg.value = Math.round(wPct * 10) / 10
      gpa.value = Math.round(wGpa * 100) / 100
    } else {
      gradeAvg.value = null
      gpa.value = null
    }

    // Phase 16 — yangi widgetlar (parallel)
    const [act, exams, notifs] = await Promise.all([
      activityApi.my(activityPeriod.value).catch(() => null),
      examsApi.my({ page_size: 20 }).catch(() => ({ items: [], total: 0 })),
      notificationsApi.list({ unread_only: true, page: 1, page_size: 5 }).catch(
        () => ({ items: [], total: 0, unread_count: 0 }),
      ),
    ])
    activityData.value = act

    // Yaqin imtihonlar: available_from <= +7d AND available_until > now
    const now = Date.now()
    const weekAhead = now + 7 * 24 * 60 * 60 * 1000
    upcomingExams.value = exams.items
      .filter((ex) => {
        if (ex.status !== 'published') return false
        const from = ex.available_from ? new Date(ex.available_from).getTime() : 0
        const until = ex.available_until
          ? new Date(ex.available_until).getTime()
          : Infinity
        return from <= weekAhead && until > now
      })
      .sort((a, b) => {
        const av = a.available_from ? new Date(a.available_from).getTime() : 0
        const bv = b.available_from ? new Date(b.available_from).getTime() : 0
        return av - bv
      })
      .slice(0, 5)

    topNotifications.value = notifs.items.slice(0, 5)
    unreadNotificationCount.value = notifs.unread_count ?? notifs.items.length
  } catch {
    // ignore
  }
}

// Phase 16 — period switcher
async function changeActivityPeriod(p: 7 | 30 | 365) {
  activityPeriod.value = p
  try {
    activityData.value = await activityApi.my(p)
  } catch {
    // ignore
  }
}

async function loadTeacherData() {
  if (!auth.user) return
  try {
    const my = await coursesApi.list({
      primary_author_id: auth.user.id,
      page_size: 100,
    })
    myCoursesCount.value = my.total
    recentCourses.value = my.items.slice(0, 3)

    const inbox = await assignmentsApi.inbox({
      status: 'submitted',
      page_size: 1,
    })
    pendingGradingCount.value = inbox.total
  } catch {
    // ignore
  }
}

async function loadLive() {
  try {
    const nowIso = new Date().toISOString()
    const [up, now] = await Promise.all([
      liveSessionsApi.list({
        status: 'scheduled',
        starts_after: nowIso,
        page_size: 5,
      }),
      liveSessionsApi.list({ status: 'live', page_size: 5 }),
    ])
    upcomingLive.value = up.items
      .slice()
      .sort(
        (a, b) =>
          new Date(a.scheduled_start).getTime() -
          new Date(b.scheduled_start).getTime(),
      )
      .slice(0, 3)
    liveNow.value = now.items.slice(0, 3)
  } catch {
    upcomingLive.value = []
    liveNow.value = []
  }
}

onMounted(async () => {
  if (isTeacher.value) await loadTeacherData()
  else await loadStudentData()
  if (auth.hasPermission('live.read')) await loadLive()
})

const today = computed(() => {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      day: 'numeric',
      month: 'long',
    }).format(new Date())
  } catch {
    return ''
  }
})

const firstName = computed(() => {
  return auth.user?.full_name?.split(' ')[0] ?? auth.user?.email?.split('@')[0] ?? ''
})

function fmtTime(s: string): string {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}

function daysUntil(dateStr: string): number {
  const due = new Date(dateStr).getTime()
  const now = Date.now()
  return Math.max(0, Math.ceil((due - now) / (1000 * 60 * 60 * 24)))
}

function deadlineVariant(days: number): 'default' | 'warning' | 'danger' {
  if (days <= 2) return 'danger'
  if (days <= 7) return 'warning'
  return 'default'
}

function fmtDeadline(s: string): string {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      day: '2-digit',
      month: 'short',
    }).format(new Date(s)).toUpperCase()
  } catch {
    return s
  }
}

function progressOf(c: Course): number {
  return courseProgress.value[c.id] ?? 0
}
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb>
      <span>{{ t('dashboard.crumb_home') }}</span>
    </UiBreadcrumb>
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">
          {{ t('dashboard.greeting', { name: firstName }) }} 👋
        </h1>
        <p class="page-subtitle">
          {{ t('dashboard.today') }}, {{ today }} ·
          <template v-if="isTeacher">
            {{ t('dashboard.teacher_subtitle', { pending: pendingGradingCount, live: liveNow.length + upcomingLive.length }) }}
          </template>
          <template v-else>
            {{ t('dashboard.student_subtitle', { tasks: activeAssignmentsCount, live: liveNow.length + upcomingLive.length }) }}
          </template>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <UiButton
          v-if="isTeacher"
          size="sm"
          @click="router.push({ name: 'my-courses' })"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M7 3v8M3 7h8" />
          </svg>
          {{ t('dashboard.btn_new_course') }}
        </UiButton>
        <template v-else>
          <UiButton
            variant="outline"
            size="sm"
            @click="router.push({ name: 'achievements' })"
          >
            ★ {{ t('nav.achievements') }}
          </UiButton>
          <UiButton size="sm" @click="router.push({ name: 'my-learning' })">
            {{ t('dashboard.btn_my_courses') }}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 7h8M7 3l4 4-4 4" />
            </svg>
          </UiButton>
        </template>
      </div>
    </div>
  </div>

  <!-- 4-STAT GRID -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
    <template v-if="isTeacher">
      <UiStatCard
        :label="t('dashboard.stat_active_courses')"
        :value="String(myCoursesCount)"
        :trend="{ direction: 'up', text: t('dashboard.trend_courses_new') }"
      />
      <UiStatCard
        :label="t('dashboard.stat_students')"
        :value="String(studentsCount || '—')"
        :hint="t('dashboard.hint_students')"
      />
      <UiStatCard
        :label="t('dashboard.stat_pending_grading')"
        :value="String(pendingGradingCount)"
        tone="warning"
        :hint="t('dashboard.hint_urgent')"
      />
      <UiStatCard
        :label="t('dashboard.stat_avg_grade')"
        value="—"
        :hint="t('dashboard.hint_ph6')"
      />
    </template>
    <template v-else>
      <UiStatCard
        :label="t('dashboard.stat_active_courses')"
        :value="String(enrolledCount)"
        :trend="{ direction: 'up', text: t('dashboard.trend_courses_semester') }"
      />
      <UiStatCard
        :label="t('dashboard.stat_points')"
        :value="String(gamifStats?.total_points ?? 0)"
        :hint="gamifStats?.rank_total
          ? t('dashboard.hint_rank', { rank: gamifStats.rank_total })
          : t('dashboard.hint_no_rank')"
      />
      <UiStatCard
        :label="t('dashboard.stat_badges')"
        :value="String(gamifStats?.badges_count ?? 0)"
        :hint="t('dashboard.hint_badges')"
      />
      <UiStatCard
        :label="t('dashboard.stat_certificates')"
        :value="String(certificatesCount)"
        :hint="t('dashboard.hint_certificates')"
      />
    </template>
  </div>

  <!-- 2-COLUMN LAYOUT (wireframe 04: 2fr + 1fr) -->
  <div class="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
    <!-- LEFT COLUMN -->
    <div class="flex flex-col gap-4">
      <!-- "Davom etish" / Continue learning -->
      <UiCard no-padding>
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.continue_title') }}</span>
          <button
            type="button"
            class="font-mono text-[12px] text-muted-foreground hover:text-foreground"
            @click="router.push({ name: isStudent ? 'my-learning' : 'my-courses' })"
          >
            {{ t('dashboard.see_all') }} →
          </button>
        </div>
        <div v-if="recentCourses.length === 0" class="p-6 text-center text-[12px] text-muted-foreground">
          {{ t('dashboard.no_courses') }}
        </div>
        <div v-else>
          <div
            v-for="(c, i) in recentCourses"
            :key="c.id"
            class="flex gap-4 p-4 items-center"
            :class="i < recentCourses.length - 1 ? 'border-b border-border' : ''"
          >
            <div class="w-20 h-[60px] flex-shrink-0">
              <UiImagePlaceholder
                v-if="!c.cover_image_url"
                aspect="auto"
                :label="t('dashboard.cover')"
              />
              <img
                v-else
                :src="c.cover_image_url"
                :alt="c.title"
                class="w-full h-full object-cover rounded-md"
              />
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-1">
                {{ c.type ? c.type.toUpperCase() : t('dashboard.course_type_default') }}
              </div>
              <div class="font-semibold text-[14px] mb-1.5 truncate">{{ c.title }}</div>
              <div class="flex items-center gap-3">
                <UiProgressBar :value="progressOf(c)" />
                <span class="font-mono text-[11px] text-muted-foreground shrink-0">
                  {{ progressOf(c) }}%
                </span>
              </div>
            </div>
            <UiButton
              variant="outline"
              size="sm"
              @click="router.push({ name: isStudent ? 'course-player' : 'course-builder', params: { id: c.id } })"
            >
              {{ t('dashboard.btn_continue') }}
            </UiButton>
          </div>
        </div>
      </UiCard>

      <!-- Activity chart — real data, period switcher (Phase 16) -->
      <UiCard no-padding>
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.activity_title') }}</span>
          <div class="flex gap-1">
            <button
              v-for="p in [7, 30, 365] as const"
              :key="p"
              type="button"
              class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
              :class="
                activityPeriod === p
                  ? 'bg-muted text-foreground'
                  : 'text-muted-foreground hover:bg-muted'
              "
              @click="changeActivityPeriod(p)"
            >
              {{
                p === 7
                  ? t('dashboard.range_7d')
                  : p === 30
                  ? t('dashboard.range_30d')
                  : t('dashboard.range_year')
              }}
            </button>
          </div>
        </div>
        <div class="p-5">
          <UiChartBar v-if="weekActivity.length > 0" :items="weekActivity" :height="180" />
          <div
            v-else
            class="h-[180px] flex items-center justify-center text-[12px] text-muted-foreground"
          >
            {{ t('dashboard.no_activity') }}
          </div>
          <div class="mt-8 pt-4 border-t border-border flex flex-wrap gap-4 justify-between text-[12px] text-muted-foreground">
            <div>
              {{ t('dashboard.total') }}:
              <span class="text-foreground font-mono font-medium">
                {{ totalHours }} {{ t('dashboard.hours') }}
              </span>
            </div>
            <div>
              {{ t('dashboard.most_active') }}:
              <span class="text-foreground font-mono font-medium">{{ mostActiveLabel }}</span>
            </div>
            <div>
              {{ t('dashboard.streak') }}:
              <span
                class="font-mono font-medium"
                :class="streakDays > 0 ? 'text-success-600' : 'text-muted-foreground'"
              >
                {{ streakDays }} {{ t('dashboard.days') }} {{ streakDays >= 3 ? '🔥' : '' }}
              </span>
            </div>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- RIGHT COLUMN -->
    <div class="flex flex-col gap-4">
      <!-- Akademik ko'rsatkich (GPA) — talaba -->
      <UiCard v-if="!isTeacher" no-padding>
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.academic_title') }}</span>
          <button
            type="button"
            class="font-mono text-[12px] text-muted-foreground hover:text-foreground"
            @click="router.push({ name: 'grades' })"
          >
            {{ t('dashboard.see_all') }} →
          </button>
        </div>
        <div class="p-5 flex items-center gap-5">
          <div class="text-center shrink-0">
            <div class="text-[34px] font-bold tabular-nums leading-none text-[#1f3a5f] dark:text-[#d9b962]">
              {{ gpa !== null ? gpa.toFixed(2) : '—' }}
            </div>
            <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mt-1.5">
              GPA · 4.0
            </div>
          </div>
          <div class="flex-1 grid grid-cols-2 gap-3 text-center border-l border-border pl-5">
            <div>
              <div class="text-[18px] font-semibold tabular-nums">
                {{ gradeAvg !== null ? `${gradeAvg}%` : '—' }}
              </div>
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                {{ t('dashboard.academic_avg') }}
              </div>
            </div>
            <div>
              <div class="text-[18px] font-semibold tabular-nums">{{ gradedCount }}</div>
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                {{ t('dashboard.academic_graded') }}
              </div>
            </div>
          </div>
        </div>
      </UiCard>

      <!-- Bugungi jadval (live + scheduled) -->
      <UiCard no-padding>
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.today_schedule') }}</span>
          <UiBadge>{{ liveNow.length + upcomingLive.length }} {{ t('dashboard.classes_short') }}</UiBadge>
        </div>
        <div
          v-if="liveNow.length === 0 && upcomingLive.length === 0"
          class="p-6 text-center text-[12px] text-muted-foreground"
        >
          {{ t('dashboard.no_classes') }}
        </div>
        <div v-else>
          <div
            v-for="s in liveNow"
            :key="`now-${s.id}`"
            class="px-5 py-3 border-b border-border flex gap-3 items-start cursor-pointer hover:bg-muted/30"
            @click="router.push({ name: 'live-lobby', params: { id: s.id } })"
          >
            <div class="font-mono text-[11px] text-muted-foreground w-12 shrink-0">
              {{ fmtTime(s.scheduled_start) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium text-[13px] truncate">{{ s.title }}</div>
              <div class="text-[11px] text-muted-foreground mt-0.5">
                Live · {{ s.duration_minutes }} {{ t('dashboard.min_short') }}
              </div>
              <UiBadge variant="success" with-dot class="mt-1.5">
                {{ t('live.status_live') }}
              </UiBadge>
            </div>
          </div>
          <div
            v-for="(s, i) in upcomingLive"
            :key="`up-${s.id}`"
            class="px-5 py-3 flex gap-3 items-start"
            :class="i < upcomingLive.length - 1 ? 'border-b border-border' : ''"
          >
            <div class="font-mono text-[11px] text-muted-foreground w-12 shrink-0">
              {{ fmtTime(s.scheduled_start) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium text-[13px] truncate">{{ s.title }}</div>
              <div class="text-[11px] text-muted-foreground mt-0.5">
                {{ s.duration_minutes }} {{ t('dashboard.min_short') }}
              </div>
              <UiBadge variant="info" with-dot class="mt-1.5">
                {{ t('dashboard.upcoming') }}
              </UiBadge>
            </div>
          </div>
        </div>
      </UiCard>

      <!-- Yaqin muddatlar / Deadlines -->
      <UiCard
        v-if="!isTeacher && recentAssignments.length > 0"
        no-padding
      >
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.upcoming_deadlines') }}</span>
          <UiBadge
            v-if="recentAssignments.some((a) => daysUntil(a.due_date) <= 2)"
            variant="danger"
          >
            {{ recentAssignments.filter((a) => daysUntil(a.due_date) <= 2).length }}
            {{ t('dashboard.urgent') }}
          </UiBadge>
        </div>
        <div class="p-5 space-y-3">
          <div
            v-for="a in recentAssignments"
            :key="a.id"
            class="cursor-pointer hover:opacity-80"
            @click="router.push({ name: 'assignment-detail', params: { id: a.id } })"
          >
            <div class="flex justify-between items-center mb-1">
              <span class="text-[13px] font-medium truncate">{{ a.title }}</span>
              <UiBadge :variant="deadlineVariant(daysUntil(a.due_date))">
                {{ daysUntil(a.due_date) }} {{ t('dashboard.days_short') }}
              </UiBadge>
            </div>
            <div class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {{ fmtDeadline(a.due_date) }}
            </div>
          </div>
        </div>
      </UiCard>

      <!-- Phase 16 — Yaqin imtihonlar (talaba) -->
      <UiCard
        v-if="!isTeacher && upcomingExams.length > 0"
        no-padding
      >
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.upcoming_exams') }}</span>
          <UiBadge>{{ upcomingExams.length }}</UiBadge>
        </div>
        <ul class="divide-y divide-border">
          <li
            v-for="ex in upcomingExams"
            :key="ex.id"
            class="px-5 py-3 cursor-pointer hover:bg-muted/40"
            @click="router.push({ name: 'exam-lobby', params: { id: ex.id } })"
          >
            <div class="flex items-start justify-between gap-2 mb-1">
              <span class="text-[13px] font-medium truncate">{{ ex.title }}</span>
              <UiBadge :variant="ex.type === 'final' ? 'danger' : ex.type === 'midterm' ? 'warning' : 'default'">
                {{ t(`exams.type_${ex.type}`) }}
              </UiBadge>
            </div>
            <div class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              <span v-if="ex.available_from">
                {{ t('dashboard.exam_starts', { date: fmtDeadline(ex.available_from) }) }}
              </span>
              <span v-else-if="ex.available_until">
                {{ t('dashboard.exam_ends', { date: fmtDeadline(ex.available_until) }) }}
              </span>
              · {{ ex.duration_minutes }} {{ t('dashboard.min_short') }}
            </div>
          </li>
        </ul>
      </UiCard>

      <!-- Phase 16 — So'nggi o'qilmagan bildirishnomalar (talaba) -->
      <UiCard
        v-if="!isTeacher && topNotifications.length > 0"
        no-padding
      >
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.unread_notifications') }}</span>
          <button
            type="button"
            class="font-mono text-[12px] text-muted-foreground hover:text-foreground"
            @click="router.push({ name: 'notifications' })"
          >
            {{ unreadNotificationCount }} →
          </button>
        </div>
        <ul class="divide-y divide-border">
          <li
            v-for="n in topNotifications"
            :key="n.id"
            class="px-5 py-3 cursor-pointer hover:bg-muted/40"
            @click="n.action_url && router.push(n.action_url)"
          >
            <div class="text-[13px] font-medium truncate mb-0.5">{{ n.title }}</div>
            <div v-if="n.body" class="text-[12px] text-muted-foreground truncate">
              {{ n.body }}
            </div>
          </li>
        </ul>
      </UiCard>

      <!-- Phase 13 — yaqinda olingan nishonlar (faqat talaba) -->
      <UiCard
        v-if="!isTeacher && (gamifStats?.recent_badges?.length ?? 0) > 0"
        no-padding
      >
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.recent_badges') }}</span>
          <button
            type="button"
            class="font-mono text-[12px] text-muted-foreground hover:text-foreground"
            @click="router.push({ name: 'achievements' })"
          >
            {{ t('dashboard.see_all') }} →
          </button>
        </div>
        <ul class="divide-y divide-border">
          <li
            v-for="ub in gamifStats?.recent_badges ?? []"
            :key="ub.badge.id"
            class="px-5 py-3 flex items-center gap-3"
          >
            <div
              class="w-9 h-9 rounded-md bg-foreground text-background grid place-items-center text-[16px] shrink-0"
            >
              ★
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-[13px] font-medium truncate">
                {{ ub.badge.title }}
              </div>
              <div class="text-[11px] font-mono text-muted-foreground">
                +{{ ub.badge.points_reward }} {{ t('dashboard.points_short') }}
              </div>
            </div>
          </li>
        </ul>
      </UiCard>

      <!-- Announcements placeholder (faqat pedagog uchun yoki badge yo'q bo'lsa) -->
      <UiCard v-else no-padding>
        <div class="px-5 py-4 border-b border-border">
          <span class="text-sm font-semibold">{{ t('dashboard.announcements') }}</span>
        </div>
        <div class="px-5 py-3">
          <div class="py-2">
            <div class="font-mono text-[10px] text-muted-foreground mb-1 uppercase tracking-wider">
              {{ today }} · {{ t('dashboard.system') }}
            </div>
            <div class="text-[13px] leading-snug">
              {{ t('dashboard.announcement_welcome') }}
            </div>
          </div>
        </div>
      </UiCard>
    </div>
  </div>
</template>
