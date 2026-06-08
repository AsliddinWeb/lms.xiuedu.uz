<script setup lang="ts">
/**
 * Baholar (Grades) — talaba transcript.
 *
 * Real backend: GET /me/gradebook (kursli baholar) + sertifikatlar.
 * GPA 4.0 shkalada harf bandlari bo'yicha kreditga vaznli hisoblanadi.
 * Tarix/Reyting tablari keyingi fazalarda.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiChartBar from '@shared/components/ui/UiChartBar.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import {
  gradebookApi,
  type GradebookRow,
  type SemesterGrades,
} from '@shared/api/courses'
import {
  certificatesApi,
  type CertificateMyItem,
} from '@shared/api/certificates'
import { calendarsApi } from '@shared/api/academic'
import {
  gamificationApi,
  type LeaderboardResponse,
} from '@shared/api/gamification'
import { useAuthStore } from '@shared/stores/auth'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import { formatFullDate } from '@shared/utils/datetime'
import type { AcademicCalendar } from '@shared/types/academic'

const { t, locale } = useI18n()
const auth = useAuthStore()

type Tab = 'current' | 'history' | 'ranking' | 'certificates'
const activeTab = ref<Tab>('current')

// Phase 13.20 — real backenddan yuklanadi
const gpa = ref<number | null>(null)
const semesterAvg = ref<number | null>(null)
const totalCredits = ref(0)

// Reyting, programCredits, semestrlar tarixi — backendda hali yo'q (Phase 14+).
const programCredits = 240

const calendar = ref<AcademicCalendar | null>(null)

// 4.0 GPA — backend harf bandlariga mos: >=86 A'lo, >=71 Yaxshi, >=55 Qoniqarli
function gpaPoints(percent: number): number {
  if (percent >= 86) return 4
  if (percent >= 71) return 3
  if (percent >= 55) return 2
  return 0
}

const academicYear = computed(() => calendar.value?.academic_year ?? '')
const currentSemesterName = computed(() => {
  const sems = (calendar.value?.semesters ?? []) as Array<Record<string, unknown>>
  const today = Date.now()
  for (const s of sems) {
    const start = (s.start ?? s.start_date) as string | undefined
    const end = (s.end ?? s.end_date) as string | undefined
    if (
      start &&
      end &&
      today >= new Date(start).getTime() &&
      today <= new Date(end).getTime() + 86_400_000
    ) {
      return String(s.name ?? '')
    }
  }
  return ''
})

const semesterBars = computed(() => {
  // Hozircha faqat joriy semestr ko'rsatiladi — tarix Phase 14
  if (semesterAvg.value === null) return []
  return [{ label: 'S1', value: semesterAvg.value }]
})

const currentGrades = ref<GradebookRow[]>([])
const myCertificates = ref<CertificateMyItem[]>([])
const leaderboard = ref<LeaderboardResponse | null>(null)
const history = ref<SemesterGrades[]>([])

const tabs = computed(() => [
  { id: 'current', label: t('grades.tab_current') },
  { id: 'history', label: t('grades.tab_history') },
  { id: 'ranking', label: t('grades.tab_ranking') },
  // Phase 13.20 — sertifikatlar tabi real ma'lumotlardan
  { id: 'certificates', label: t('grades.tab_certificates') },
])

async function loadGradebook() {
  try {
    const rows = await gradebookApi.myGradebook()
    currentGrades.value = rows
    totalCredits.value = rows.reduce((acc, r) => acc + r.credits, 0)

    // Faqat baholangan kurslar (grade_number > 0), kreditga vaznli
    const graded = rows.filter(
      (r) => Number.isFinite(r.grade_number) && r.grade_number > 0,
    )
    if (graded.length > 0) {
      const cr = graded.reduce((a, r) => a + r.credits, 0) || 1
      const wPct = graded.reduce((a, r) => a + r.grade_number * r.credits, 0) / cr
      const wGpa = graded.reduce((a, r) => a + gpaPoints(r.grade_number) * r.credits, 0) / cr
      semesterAvg.value = Math.round(wPct * 10) / 10
      gpa.value = Math.round(wGpa * 100) / 100
    } else {
      semesterAvg.value = null
      gpa.value = null
    }
  } catch {
    currentGrades.value = []
  }
}

async function loadCertificates() {
  try {
    myCertificates.value = await certificatesApi.listMine()
  } catch {
    myCertificates.value = []
  }
}

async function loadLeaderboard() {
  try {
    leaderboard.value = await gamificationApi.leaderboard('total', 20)
  } catch {
    leaderboard.value = null
  }
}

async function loadHistory() {
  try {
    history.value = await gradebookApi.history()
  } catch {
    history.value = []
  }
}

function fmtDate(iso: string): string {
  return formatFullDate(iso, locale.value)
}

const downloading = ref(false)
async function downloadTranscript() {
  downloading.value = true
  try {
    const blob = await gradebookApi.downloadCsv()
    downloadBlob(blob, timestampedFilename('transcript'))
  } catch {
    // ignore
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    loadGradebook(),
    loadCertificates(),
    loadLeaderboard(),
    loadHistory(),
  ])
  if (auth.user?.tenant_id) {
    calendarsApi
      .getCurrent(auth.user.tenant_id)
      .then((c) => {
        calendar.value = c
      })
      .catch(() => undefined)
  }
})
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('grades.title')]" />
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('grades.title') }}</h1>
        <p class="page-subtitle">
          <template v-if="currentSemesterName">{{ currentSemesterName }} · </template>
          <template v-if="academicYear">{{ academicYear }} · </template>
          {{ auth.user?.full_name }}
        </p>
      </div>
      <UiButton
        variant="outline"
        size="sm"
        :loading="downloading"
        @click="downloadTranscript"
      >
        📥 {{ t('grades.btn_download_transcript') }}
      </UiButton>
    </div>
  </div>

  <!-- TOP STATS: GPA card (dark) + semester chart -->
  <div class="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-4 mb-6">
    <!-- GPA card — wireframe signature dark element -->
    <div class="bg-foreground text-background rounded-lg p-6">
      <div class="font-mono text-[11px] uppercase tracking-widest opacity-60 mb-3">
        {{ t('grades.gpa_label') }}
      </div>
      <div class="flex items-baseline gap-2 mb-1">
        <div class="text-[56px] font-semibold tracking-tightest leading-none tabular-nums">
          {{ gpa ?? '—' }}
        </div>
        <div class="opacity-50 font-mono text-sm">/ 4.0</div>
      </div>
      <div class="text-xs opacity-70 mb-6">
        {{ t('grades.gpa_hint') }}
      </div>

      <div class="grid grid-cols-2 gap-4 pt-4 border-t border-white/10">
        <div>
          <div class="opacity-50 font-mono text-[10px] uppercase tracking-wider">
            {{ t('grades.semester_avg') }}
          </div>
          <div class="font-mono text-lg font-semibold mt-1 tabular-nums">
            {{ semesterAvg !== null ? `${semesterAvg}%` : '—' }}
          </div>
        </div>
        <div>
          <div class="opacity-50 font-mono text-[10px] uppercase tracking-wider">
            {{ t('grades.credits') }}
          </div>
          <div class="font-mono text-lg font-semibold mt-1 tabular-nums">
            {{ totalCredits }} / {{ programCredits }}
          </div>
        </div>
      </div>
    </div>

    <!-- Semester chart -->
    <div class="bg-card border border-border rounded-lg overflow-hidden">
      <div class="px-5 py-4 border-b border-border flex items-center justify-between">
        <span class="text-sm font-semibold">{{ t('grades.semester_chart_title') }}</span>
        <UiBadge>{{ semesterBars.length }} {{ t('grades.semester_short') }}</UiBadge>
      </div>
      <div class="p-5">
        <UiChartBar :items="semesterBars" :height="160" />
        <div
          v-if="semesterBars.length"
          class="mt-8 pt-4 border-t border-border flex justify-between text-xs"
        >
          <div>
            <span class="text-muted-foreground">{{ t('grades.current_semester') }}:</span>
            <span class="font-mono font-semibold ml-1">{{ semesterAvg }}</span>
          </div>
          <div>
            <span class="text-muted-foreground">{{ t('grades.highest') }}:</span>
            <span class="font-mono font-semibold text-success-600 ml-1">{{ Math.max(...semesterBars.map(s => s.value)) }}</span>
          </div>
          <div>
            <span class="text-muted-foreground">{{ t('grades.lowest') }}:</span>
            <span class="font-mono font-semibold ml-1">{{ Math.min(...semesterBars.map(s => s.value)) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- TABS -->
  <UiTabs v-model="activeTab" :tabs="tabs" />

  <!-- CURRENT SEMESTER -->
  <div
    v-if="activeTab === 'current'"
    class="bg-card border border-border rounded-lg overflow-hidden"
  >
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <span class="text-sm font-semibold">
        <template v-if="currentSemesterName">{{ currentSemesterName }} · </template>{{ t('grades.subjects_grades') }}
      </span>
      <span class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
        {{ currentGrades.length }} {{ t('grades.subjects_short') }} ·
        {{ currentGrades.reduce((acc, g) => acc + g.credits, 0) }} {{ t('grades.credits_short') }}
      </span>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_subject') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_credits') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_current') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_midterm') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_final') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_total') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_grade') }}
            </th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-if="currentGrades.length === 0"
          >
            <td colspan="8" class="px-4 py-12 text-center text-muted-foreground">
              {{ t('grades.empty') }}
            </td>
          </tr>
          <tr
            v-for="g in currentGrades"
            :key="g.course_id"
            class="border-t border-border hover:bg-muted/30"
          >
            <td class="px-4 py-3">
              <div class="font-medium">{{ g.title }}</div>
              <div class="text-[11px] text-muted-foreground">{{ g.teacher }}</div>
            </td>
            <td class="px-4 py-3 font-mono text-[12px]">{{ g.credits }}</td>
            <td class="px-4 py-3 font-mono">{{ g.current_avg }}</td>
            <td class="px-4 py-3 font-mono">{{ g.midterm }}</td>
            <td class="px-4 py-3 font-mono text-muted-foreground">{{ g.final }}</td>
            <td class="px-4 py-3 font-mono font-semibold">{{ g.total }}</td>
            <td class="px-4 py-3">
              <UiBadge :variant="g.grade_variant">
                {{ g.grade_letter }}<template v-if="g.grade_number"> · {{ g.grade_number }}</template>
              </UiBadge>
            </td>
            <td class="px-4 py-3 text-right">
              <UiButton
                variant="ghost"
                size="sm"
                @click="$router.push({ name: 'course-detail', params: { id: g.course_id } })"
              >
                {{ t('common.view') }}
              </UiButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Phase 13.20 — Certificates tab: real ma'lumotlar -->
  <div
    v-else-if="activeTab === 'certificates'"
    class="bg-card border border-border rounded-lg overflow-hidden"
  >
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <span class="text-sm font-semibold">{{ t('certificates.title') }}</span>
      <span class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
        {{ myCertificates.length }}
      </span>
    </div>
    <div
      v-if="myCertificates.length === 0"
      class="py-12 text-center text-[13px] text-muted-foreground"
    >
      {{ t('certificates.empty') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead>
        <tr class="bg-muted">
          <th class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {{ t('certificates.col_number') }}
          </th>
          <th class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {{ t('certificates.col_course') }}
          </th>
          <th class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {{ t('certificates.col_issued') }}
          </th>
          <th class="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="c in myCertificates"
          :key="c.id"
          class="border-t border-border"
        >
          <td class="px-4 py-3 font-mono">{{ c.certificate_number }}</td>
          <td class="px-4 py-3">{{ c.course_title }}</td>
          <td class="px-4 py-3 font-mono">{{ fmtDate(c.issued_at) }}</td>
          <td class="px-4 py-3 text-right">
            <UiButton
              variant="outline"
              size="sm"
              @click="$router.push({ name: 'my-certificates' })"
            >
              {{ t('common.view') }}
            </UiButton>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- RANKING — gamifikatsiya leaderboard -->
  <div
    v-else-if="activeTab === 'ranking'"
    class="bg-card border border-border rounded-lg overflow-hidden"
  >
    <div class="px-5 py-4 border-b border-border flex items-center justify-between">
      <span class="text-sm font-semibold">{{ t('grades.ranking') }}</span>
      <span
        v-if="leaderboard?.me_rank"
        class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider"
      >
        {{ t('grades.my_rank') }}: #{{ leaderboard.me_rank }}
      </span>
    </div>
    <div
      v-if="!leaderboard || leaderboard.items.length === 0"
      class="py-12 text-center text-[13px] text-muted-foreground"
    >
      {{ t('grades.empty') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead>
        <tr class="bg-muted">
          <th class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground w-20">
            {{ t('grades.col_rank') }}
          </th>
          <th class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {{ t('grades.col_student') }}
          </th>
          <th class="text-right px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {{ t('grades.col_points') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="it in leaderboard.items"
          :key="it.user_id"
          class="border-t border-border"
          :class="it.user_id === auth.user?.id ? 'bg-foreground/5 font-semibold' : 'hover:bg-muted/30'"
        >
          <td class="px-4 py-3 font-mono tabular-nums">
            <span v-if="it.rank === 1">🥇</span>
            <span v-else-if="it.rank === 2">🥈</span>
            <span v-else-if="it.rank === 3">🥉</span>
            <span v-else>{{ it.rank }}</span>
          </td>
          <td class="px-4 py-3">
            {{ it.full_name }}
            <span
              v-if="it.user_id === auth.user?.id"
              class="ml-1.5 font-mono text-[10px] text-muted-foreground"
            >
              ({{ t('grades.you') }})
            </span>
          </td>
          <td class="px-4 py-3 text-right font-mono font-semibold tabular-nums">{{ it.points }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- HISTORY — semestr bo'yicha to'liq tarix -->
  <div v-else class="space-y-5">
    <div
      v-if="history.length === 0"
      class="text-center py-16 border border-dashed border-border rounded-lg"
    >
      <p class="text-muted-foreground">{{ t('grades.history_empty') }}</p>
    </div>
    <div
      v-for="(sem, i) in history"
      :key="i"
      class="bg-card border border-border rounded-lg overflow-hidden"
    >
      <div class="px-5 py-4 border-b border-border flex flex-wrap items-center justify-between gap-3">
        <div>
          <span class="text-sm font-semibold capitalize">{{ sem.semester }}</span>
          <span class="font-mono text-[11px] text-muted-foreground ml-2">{{ sem.academic_year }}</span>
        </div>
        <div class="flex items-center gap-4 font-mono text-[12px]">
          <span>
            {{ t('grades.gpa_label') }}:
            <span class="font-semibold text-foreground">{{ sem.gpa ?? '—' }}</span>
          </span>
          <span class="text-muted-foreground">{{ sem.avg !== null ? sem.avg + '%' : '—' }}</span>
          <span class="text-muted-foreground">
            {{ sem.total_credits }} {{ t('grades.credits_short') }}
          </span>
        </div>
      </div>
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th class="text-left px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_subject') }}
            </th>
            <th class="text-left px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_credits') }}
            </th>
            <th class="text-left px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('grades.col_grade') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in sem.courses" :key="c.course_id" class="border-t border-border">
            <td class="px-4 py-2.5 font-medium">{{ c.title }}</td>
            <td class="px-4 py-2.5 font-mono">{{ c.credits }}</td>
            <td class="px-4 py-2.5">
              <UiBadge :variant="c.grade_variant">
                {{ c.grade_letter }}<template v-if="c.grade_number"> · {{ c.grade_number }}</template>
              </UiBadge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
