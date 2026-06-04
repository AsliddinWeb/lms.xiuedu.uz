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
 * Ikki ko'rinish: Agenda (kunlar bo'yicha) va oylik Kalendar.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import { coursesApi } from '@shared/api/courses'
import { calendarsApi } from '@shared/api/academic'
import { assignmentsApi } from '@shared/api/assignments'
import { examsApi } from '@shared/api/exams'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { AcademicCalendar } from '@shared/types/academic'
import LiveCalendarButton from '@user/components/live/LiveCalendarButton.vue'

const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()
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

type ViewMode = 'agenda' | 'calendar'
const viewMode = ref<ViewMode>('agenda')

// Tur filtri (har uchala tur boshida yoqilgan)
const activeTypes = ref<Record<ScheduleType, boolean>>({
  live: true,
  exam: true,
  assignment: true,
})
const calendar = ref<AcademicCalendar | null>(null)

// ---- Filtr/ko'rinish holatini URL query bilan sinxronlash (ulashsa bo'ladigan link) ----
const ALL_TYPES: ScheduleType[] = ['live', 'exam', 'assignment']

function activeTypeList(): ScheduleType[] {
  return ALL_TYPES.filter((ty) => activeTypes.value[ty])
}

// Dastlabki holatni URL'dan o'qiymiz
const qView = route.query.view
if (qView === 'calendar' || qView === 'agenda') viewMode.value = qView
const qTypes = route.query.types
if (typeof qTypes === 'string') {
  const set = new Set(qTypes.split(',').filter(Boolean))
  activeTypes.value = {
    live: set.has('live'),
    exam: set.has('exam'),
    assignment: set.has('assignment'),
  }
}

// O'zgarishni URL'ga yozamiz (history to'lib ketmasligi uchun replace)
watch(
  () => `${viewMode.value}|${activeTypeList().join(',')}`,
  () => {
    router.replace({
      query: { view: viewMode.value, types: activeTypeList().join(',') },
    })
  },
)

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

    // Akademik kalendar konteksti (semestr / ta'til) — talabaning OTM'i bo'yicha
    if (auth.user.tenant_id) {
      calendarsApi
        .getCurrent(auth.user.tenant_id)
        .then((c) => {
          calendar.value = c
        })
        .catch(() => undefined)
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

const typeMeta: Record<
  ScheduleType,
  { label: string; variant: 'info' | 'danger' | 'warning'; icon: string; dot: string }
> = {
  live: { label: 'schedule.type_live', variant: 'info', icon: '🔵', dot: 'bg-blue-500' },
  exam: { label: 'schedule.type_exam', variant: 'danger', icon: '🔴', dot: 'bg-red-500' },
  assignment: {
    label: 'schedule.type_assignment',
    variant: 'warning',
    icon: '🟡',
    dot: 'bg-amber-500',
  },
}

// ---- Sana yordamchilari ----
function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}
function dayKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function keyToDate(key: string): Date {
  const [y, m, dd] = key.split('-').map(Number)
  return new Date(y, m - 1, dd)
}
function relDayLabel(d: Date): string {
  const diff = Math.round((startOfDay(d) - startOfDay(new Date())) / 86_400_000)
  if (diff === 0) return t('schedule.today')
  if (diff === 1) return t('schedule.tomorrow')
  if (diff === -1) return t('schedule.yesterday')
  try {
    return new Intl.DateTimeFormat(locale.value, {
      weekday: 'long',
      day: '2-digit',
      month: 'long',
    }).format(d)
  } catch {
    return dayKey(d)
  }
}
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

function fmtRange(a: string, b: string): string {
  try {
    const f = new Intl.DateTimeFormat(locale.value, { day: '2-digit', month: 'short' })
    return `${f.format(new Date(a))} – ${f.format(new Date(b))}`
  } catch {
    return ''
  }
}

// Tur filtri qo'llangan eventlar
const filteredEvents = computed(() =>
  events.value.filter((e) => activeTypes.value[e.type]),
)

// Kunlar bo'yicha event indeksi (filtrlangan)
const eventsByDay = computed<Record<string, ScheduleEvent[]>>(() => {
  const m: Record<string, ScheduleEvent[]> = {}
  for (const ev of filteredEvents.value) {
    const k = dayKey(new Date(ev.start))
    ;(m[k] ??= []).push(ev)
  }
  return m
})

// Joriy semestr (bugun [start, end] oralig'ida) — JSONB kalit nomlari erkin
const currentSemester = computed<{ name: string; start: string; end: string } | null>(
  () => {
    const sems = (calendar.value?.semesters ?? []) as Array<Record<string, unknown>>
    const today = startOfDay(new Date())
    for (const s of sems) {
      const start = (s.start ?? s.start_date) as string | undefined
      const end = (s.end ?? s.end_date) as string | undefined
      if (!start || !end) continue
      if (today >= startOfDay(new Date(start)) && today <= startOfDay(new Date(end))) {
        return { name: String(s.name ?? ''), start, end }
      }
    }
    return null
  },
)

// Bugun ta'tilmi
const todayHoliday = computed<string | null>(() => {
  const hols = (calendar.value?.holidays ?? []) as Array<Record<string, unknown>>
  const k = dayKey(new Date())
  for (const h of hols) {
    const d = (h.date ?? h.day) as string | undefined
    if (d && dayKey(new Date(d)) === k) return String(h.name ?? '')
  }
  return null
})

// ---- Agenda ----
interface DayGroup {
  key: string
  label: string
  isPast: boolean
  events: ScheduleEvent[]
}
const groupedDays = computed<DayGroup[]>(() => {
  const todayMs = startOfDay(new Date())
  const groups: DayGroup[] = []
  for (const key of Object.keys(eventsByDay.value).sort()) {
    const d = keyToDate(key)
    groups.push({
      key,
      label: relDayLabel(d),
      isPast: startOfDay(d) < todayMs,
      events: eventsByDay.value[key],
    })
  }
  return groups
})

const hasEvents = computed(() => events.value.length > 0)

// ---- Kalendar ----
const now0 = new Date()
const calendarMonth = ref<Date>(new Date(now0.getFullYear(), now0.getMonth(), 1))
const selectedDay = ref<string>(dayKey(now0))

const monthLabel = computed(() => {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      month: 'long',
      year: 'numeric',
    }).format(calendarMonth.value)
  } catch {
    return ''
  }
})

const weekDayNames = computed(() => {
  const names: string[] = []
  for (let i = 0; i < 7; i++) {
    // 2024-01-01 — dushanba
    const d = new Date(2024, 0, 1 + i)
    names.push(new Intl.DateTimeFormat(locale.value, { weekday: 'short' }).format(d))
  }
  return names
})

interface Cell {
  key: string
  day: number
  inMonth: boolean
  isToday: boolean
  events: ScheduleEvent[]
}
const monthCells = computed<Cell[]>(() => {
  const m = calendarMonth.value
  const year = m.getFullYear()
  const month = m.getMonth()
  const first = new Date(year, month, 1)
  const firstDow = (first.getDay() + 6) % 7 // 0 = dushanba
  const todayK = dayKey(new Date())
  const cells: Cell[] = []
  for (let i = 0; i < 42; i++) {
    const date = new Date(year, month, 1 - firstDow + i)
    const key = dayKey(date)
    cells.push({
      key,
      day: date.getDate(),
      inMonth: date.getMonth() === month,
      isToday: key === todayK,
      events: eventsByDay.value[key] ?? [],
    })
  }
  return cells
})

const selectedDayEvents = computed(() => eventsByDay.value[selectedDay.value] ?? [])
const selectedDayLabel = computed(() => relDayLabel(keyToDate(selectedDay.value)))

function prevMonth() {
  const m = calendarMonth.value
  calendarMonth.value = new Date(m.getFullYear(), m.getMonth() - 1, 1)
}
function nextMonth() {
  const m = calendarMonth.value
  calendarMonth.value = new Date(m.getFullYear(), m.getMonth() + 1, 1)
}
function goToday() {
  const n = new Date()
  calendarMonth.value = new Date(n.getFullYear(), n.getMonth(), 1)
  selectedDay.value = dayKey(n)
}
function selectDay(key: string) {
  selectedDay.value = key
}

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
      <div class="flex items-center gap-2">
        <LiveCalendarButton />
        <!-- Ko'rinish toggle -->
        <div class="flex items-center gap-1 border border-border rounded-md p-0.5">
          <button
            type="button"
            class="px-3 py-1.5 rounded text-[12px] font-medium transition-colors"
            :class="viewMode === 'agenda' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'"
            @click="viewMode = 'agenda'"
          >
            {{ t('schedule.view_agenda') }}
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded text-[12px] font-medium transition-colors"
            :class="viewMode === 'calendar' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'"
            @click="viewMode = 'calendar'"
          >
            {{ t('schedule.view_calendar') }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Toolbar: tur filtri + akademik kontekst -->
  <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
    <div class="flex flex-wrap items-center gap-2">
      <button
        v-for="ty in (['live', 'exam', 'assignment'] as ScheduleType[])"
        :key="ty"
        type="button"
        class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-[12px] font-medium transition-colors"
        :class="activeTypes[ty]
          ? 'border-foreground bg-foreground text-background'
          : 'border-border text-muted-foreground hover:text-foreground'"
        @click="activeTypes[ty] = !activeTypes[ty]"
      >
        <span>{{ typeMeta[ty].icon }}</span>
        {{ t(typeMeta[ty].label) }}
      </button>
    </div>
    <div
      v-if="currentSemester || todayHoliday"
      class="flex flex-wrap items-center gap-3 text-[12px] text-muted-foreground"
    >
      <span v-if="currentSemester" class="inline-flex items-center gap-1.5">
        📚 <span class="font-medium text-foreground">{{ currentSemester.name }}</span>
        <span class="font-mono">{{ fmtRange(currentSemester.start, currentSemester.end) }}</span>
      </span>
      <span v-if="todayHoliday" class="inline-flex items-center gap-1.5 text-warning">
        🏖 {{ todayHoliday }}
      </span>
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

  <!-- AGENDA -->
  <div v-else-if="viewMode === 'agenda'" class="space-y-6">
    <UiEmptyState
      v-if="!groupedDays.length"
      variant="search"
      :title="t('schedule.no_filter_results')"
      :description="t('schedule.no_filter_hint')"
    />
    <section v-for="g in groupedDays" :key="g.key" :class="g.isPast ? 'opacity-60' : ''">
      <div class="flex items-center gap-3 mb-2.5">
        <h2 class="text-[13px] font-semibold capitalize">{{ g.label }}</h2>
        <div class="flex-1 h-px bg-border"></div>
        <span class="font-mono text-[11px] text-muted-foreground">
          {{ t('schedule.events_count', { n: g.events.length }) }}
        </span>
      </div>
      <div class="space-y-2">
        <article
          v-for="ev in g.events"
          :key="ev.id"
          class="border border-border rounded-lg bg-card hover:border-border-strong transition-colors cursor-pointer p-3.5 flex items-center gap-4"
          @click="open(ev)"
        >
          <div class="shrink-0 w-[52px] text-center font-mono text-[13px] font-semibold tabular-nums">
            {{ fmtTime(ev.start) }}
          </div>
          <div class="w-px self-stretch bg-border"></div>
          <div class="text-[16px] shrink-0">{{ typeMeta[ev.type].icon }}</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5 flex-wrap">
              <UiBadge :variant="typeMeta[ev.type].variant">
                {{ t(typeMeta[ev.type].label) }}
              </UiBadge>
              <span v-if="ev.courseTitle" class="font-mono text-[11px] text-muted-foreground truncate">
                {{ ev.courseTitle }}
              </span>
            </div>
            <h3 class="font-semibold text-[14px] truncate">{{ ev.title }}</h3>
          </div>
          <span class="shrink-0 text-muted-foreground">→</span>
        </article>
      </div>
    </section>
  </div>

  <!-- KALENDAR -->
  <div v-else>
    <!-- Oy navigatsiyasi -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="w-8 h-8 grid place-items-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
          @click="prevMonth"
        >
          ‹
        </button>
        <span class="text-[14px] font-semibold capitalize min-w-[150px] text-center">{{ monthLabel }}</span>
        <button
          type="button"
          class="w-8 h-8 grid place-items-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
          @click="nextMonth"
        >
          ›
        </button>
      </div>
      <UiButton variant="outline" size="sm" @click="goToday">{{ t('schedule.today') }}</UiButton>
    </div>

    <!-- Hafta kunlari -->
    <div class="grid grid-cols-7 gap-1 mb-1">
      <div
        v-for="wd in weekDayNames"
        :key="wd"
        class="text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground py-1"
      >
        {{ wd }}
      </div>
    </div>

    <!-- Oy setkasi -->
    <div class="grid grid-cols-7 gap-1">
      <button
        v-for="cell in monthCells"
        :key="cell.key"
        type="button"
        class="min-h-[58px] rounded-md border p-1.5 flex flex-col items-start text-left transition-colors"
        :class="[
          cell.inMonth ? 'border-border' : 'border-transparent opacity-40',
          cell.isToday ? 'ring-1 ring-foreground' : '',
          selectedDay === cell.key ? 'bg-muted' : 'hover:bg-muted/50',
        ]"
        @click="selectDay(cell.key)"
      >
        <span class="text-[12px]" :class="cell.isToday ? 'font-bold' : ''">{{ cell.day }}</span>
        <div class="flex flex-wrap gap-0.5 mt-auto">
          <span
            v-for="(ev, i) in cell.events.slice(0, 4)"
            :key="i"
            class="w-1.5 h-1.5 rounded-full"
            :class="typeMeta[ev.type].dot"
          ></span>
          <span v-if="cell.events.length > 4" class="text-[8px] text-muted-foreground leading-none">
            +{{ cell.events.length - 4 }}
          </span>
        </div>
      </button>
    </div>

    <!-- Tanlangan kun eventlari -->
    <div class="mt-6">
      <div class="flex items-center gap-3 mb-2.5">
        <h2 class="text-[13px] font-semibold capitalize">{{ selectedDayLabel }}</h2>
        <div class="flex-1 h-px bg-border"></div>
      </div>
      <div v-if="selectedDayEvents.length" class="space-y-2">
        <article
          v-for="ev in selectedDayEvents"
          :key="ev.id"
          class="border border-border rounded-lg bg-card hover:border-border-strong transition-colors cursor-pointer p-3.5 flex items-center gap-4"
          @click="open(ev)"
        >
          <div class="shrink-0 w-[52px] text-center font-mono text-[13px] font-semibold tabular-nums">
            {{ fmtTime(ev.start) }}
          </div>
          <div class="w-px self-stretch bg-border"></div>
          <div class="text-[16px] shrink-0">{{ typeMeta[ev.type].icon }}</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5 flex-wrap">
              <UiBadge :variant="typeMeta[ev.type].variant">
                {{ t(typeMeta[ev.type].label) }}
              </UiBadge>
              <span v-if="ev.courseTitle" class="font-mono text-[11px] text-muted-foreground truncate">
                {{ ev.courseTitle }}
              </span>
            </div>
            <h3 class="font-semibold text-[14px] truncate">{{ ev.title }}</h3>
          </div>
          <span class="shrink-0 text-muted-foreground">→</span>
        </article>
      </div>
      <p v-else class="text-[13px] text-muted-foreground py-4">
        {{ t('schedule.day_no_events') }}
      </p>
    </div>
  </div>
</template>
