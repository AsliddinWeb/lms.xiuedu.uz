<script setup lang="ts">
/**
 * Jadval (Schedule) — Phase 23.
 *
 * Vaqtga bog'liq mavjud ma'lumotlarni jamlaydigan agregat sahifa:
 *   🔵 jonli darslar (scheduled_start)
 *   🔴 imtihonlar (available_from)
 *   🟡 topshiriq muddatlari (due_date)
 * Backend kerak emas — sof frontend agregatsiya (DashboardView pattern'i).
 *
 * 23.1 — skelet + agregatsiya (sodda ro'yxat). Agenda/kalendar keyingi sub-fazalarda.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import { coursesApi } from '@shared/api/courses'
import { assignmentsApi } from '@shared/api/assignments'
import { examsApi } from '@shared/api/exams'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

type ScheduleType = 'live' | 'exam' | 'assignment'

interface ScheduleEvent {
  id: string
  type: ScheduleType
  title: string
  start: string // ISO
  end?: string | null
  courseTitle?: string
  to: RouteLocationRaw
}

const events = ref<ScheduleEvent[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  if (!auth.user) return
  loading.value = true
  error.value = null
  try {
    const [live, exams, assignments, courses] = await Promise.all([
      liveSessionsApi.list({ page_size: 100 }).catch(() => ({ items: [] })),
      examsApi.my({ page_size: 100 }).catch(() => ({ items: [] })),
      assignmentsApi
        .list({ mine: true, is_published: true, page_size: 100 })
        .catch(() => ({ items: [] })),
      coursesApi
        .list({ enrolled_user_id: auth.user.id, page_size: 100 })
        .catch(() => ({ items: [] })),
    ])

    const courseTitle: Record<number, string> = {}
    for (const c of courses.items) courseTitle[c.id] = c.title

    const out: ScheduleEvent[] = []

    for (const s of live.items) {
      if (s.status === 'ended' || s.status === 'cancelled') continue
      out.push({
        id: `live-${s.id}`,
        type: 'live',
        title: s.title,
        start: s.scheduled_start,
        end: s.scheduled_end,
        courseTitle: s.course_id ? courseTitle[s.course_id] : undefined,
        to: { name: 'live-room', params: { id: String(s.id) } },
      })
    }

    for (const ex of exams.items) {
      if (!ex.available_from) continue
      out.push({
        id: `exam-${ex.id}`,
        type: 'exam',
        title: ex.title,
        start: ex.available_from,
        end: ex.available_until,
        courseTitle: courseTitle[ex.course_id],
        to: { name: 'exam-lobby', params: { id: String(ex.id) } },
      })
    }

    for (const a of assignments.items) {
      if (!a.due_date) continue
      out.push({
        id: `assignment-${a.id}`,
        type: 'assignment',
        title: a.title,
        start: a.due_date,
        courseTitle: a.course_id ? courseTitle[a.course_id] : undefined,
        to: { name: 'assignment-detail', params: { id: String(a.id) } },
      })
    }

    out.sort((x, y) => new Date(x.start).getTime() - new Date(y.start).getTime())
    events.value = out
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

const typeMeta: Record<
  ScheduleType,
  { label: string; variant: 'info' | 'danger' | 'warning'; icon: string }
> = {
  live: { label: 'schedule.type_live', variant: 'info', icon: '🔵' },
  exam: { label: 'schedule.type_exam', variant: 'danger', icon: '🔴' },
  assignment: { label: 'schedule.type_assignment', variant: 'warning', icon: '🟡' },
}

function fmtDateTime(s: string): string {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}

const hasEvents = computed(() => events.value.length > 0)

function open(ev: ScheduleEvent) {
  router.push(ev.to)
}
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('schedule.title')]" />
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('schedule.title') }}</h1>
        <p class="page-subtitle">{{ t('schedule.subtitle') }}</p>
      </div>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- LOADING -->
  <div v-if="loading && !hasEvents" class="text-center py-16 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <!-- EMPTY -->
  <UiEmptyState
    v-else-if="!hasEvents"
    :title="t('schedule.empty_title')"
    :description="t('schedule.empty_hint')"
  />

  <!-- EVENT LIST (23.1 — sodda; agenda guruhlash 23.2) -->
  <div v-else class="space-y-2.5">
    <article
      v-for="ev in events"
      :key="ev.id"
      class="border border-border rounded-lg bg-card hover:border-border-strong transition-colors cursor-pointer p-4 flex items-center gap-4"
      @click="open(ev)"
    >
      <div class="text-[18px] shrink-0">{{ typeMeta[ev.type].icon }}</div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1 flex-wrap">
          <UiBadge :variant="typeMeta[ev.type].variant">
            {{ t(typeMeta[ev.type].label) }}
          </UiBadge>
          <span v-if="ev.courseTitle" class="font-mono text-[11px] text-muted-foreground truncate">
            {{ ev.courseTitle }}
          </span>
        </div>
        <h3 class="font-semibold text-[14px] truncate">{{ ev.title }}</h3>
      </div>
      <div class="shrink-0 text-right font-mono text-[12px] text-muted-foreground">
        {{ fmtDateTime(ev.start) }}
      </div>
    </article>
  </div>
</template>
