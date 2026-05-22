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
import { coursesApi, progressApi } from '@shared/api/courses'
import { liveSessionsApi } from '@shared/api/live'
import { certificatesApi } from '@shared/api/certificates'
import {
  gamificationApi,
  type MyGamificationStats,
} from '@shared/api/gamification'
import { useAuthStore } from '@shared/stores/auth'
import type { Course } from '@shared/types/courses'
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
// Kurs progress map (course_id => percent)
const courseProgress = ref<Record<number, number>>({})

// Mock activity chart (7 kun) — real backend endpoint Phase 6+
const weekActivity = computed(() => [
  { label: t('dashboard.day_mon'), value: 45 },
  { label: t('dashboard.day_tue'), value: 70 },
  { label: t('dashboard.day_wed'), value: 85 },
  { label: t('dashboard.day_thu'), value: 60 },
  { label: t('dashboard.day_fri'), value: 92 },
  { label: t('dashboard.day_sat'), value: 30 },
  { label: t('dashboard.day_sun'), value: 25 },
])

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

    // Gamification + sertifikatlar (parallel, xatosini yutamiz)
    const [gamif, certs] = await Promise.all([
      gamificationApi.myStats().catch(() => null),
      certificatesApi.listMine().catch(() => [] as unknown[]),
    ])
    gamifStats.value = gamif
    certificatesCount.value = Array.isArray(certs) ? certs.length : 0
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
        <UiButton variant="outline" size="sm" disabled>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="3" width="10" height="9" rx="1" />
            <path d="M2 6h10M5 1v3M9 1v3" />
          </svg>
          {{ t('dashboard.btn_schedule') }}
        </UiButton>
        <UiButton
          v-if="isTeacher"
          size="sm"
          @click="router.push({ name: 'courses' })"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M7 3v8M3 7h8" />
          </svg>
          {{ t('dashboard.btn_new_course') }}
        </UiButton>
        <UiButton
          v-else
          size="sm"
          @click="router.push({ name: 'my-learning' })"
        >
          {{ t('dashboard.btn_my_courses') }}
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7h8M7 3l4 4-4 4" />
          </svg>
        </UiButton>
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
            @click="router.push({ name: isStudent ? 'my-learning' : 'courses' })"
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
                label="COVER"
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
                {{ c.type ? c.type.toUpperCase() : 'KURS' }}
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

      <!-- Activity chart -->
      <UiCard no-padding>
        <div class="px-5 py-4 border-b border-border flex items-center justify-between">
          <span class="text-sm font-semibold">{{ t('dashboard.activity_title') }}</span>
          <div class="flex gap-1">
            <button class="px-2.5 py-1 rounded text-[11px] font-medium text-muted-foreground hover:bg-muted">
              {{ t('dashboard.range_7d') }}
            </button>
            <button class="px-2.5 py-1 rounded text-[11px] font-medium bg-muted text-foreground">
              {{ t('dashboard.range_30d') }}
            </button>
            <button class="px-2.5 py-1 rounded text-[11px] font-medium text-muted-foreground hover:bg-muted">
              {{ t('dashboard.range_year') }}
            </button>
          </div>
        </div>
        <div class="p-5">
          <UiChartBar :items="weekActivity" :height="180" />
          <div class="mt-8 pt-4 border-t border-border flex justify-between text-[12px] text-muted-foreground">
            <div>
              {{ t('dashboard.total') }}:
              <span class="text-foreground font-mono font-medium">28 {{ t('dashboard.hours') }}</span>
            </div>
            <div>
              {{ t('dashboard.most_active') }}:
              <span class="text-foreground font-mono font-medium">{{ t('dashboard.day_fri') }}</span>
            </div>
            <div>
              Streak:
              <span class="text-success-600 font-mono font-medium">12 {{ t('dashboard.days') }} 🔥</span>
            </div>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- RIGHT COLUMN -->
    <div class="flex flex-col gap-4">
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
