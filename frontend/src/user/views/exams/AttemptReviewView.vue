<script setup lang="ts">
/**
 * Phase 6g — Pedagog/Admin proctoring review.
 *
 * Tabs:
 *   Hodisalar | Snapshotlar | Qaror
 *
 * Pedagog talaba attemptini ko'rib chiqadi, qoidabuzarliklar timeline'ini
 * tahlil qiladi, snapshot'larni ko'radi, qaror qabul qiladi (invalidate yoki ok).
 */

import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { attemptsApi, examsApi } from '@shared/api/exams'
import {
  proctoringApi,
  type IdReferencePhoto,
  type ProctoringEventPublic,
  type ProctoringSnapshotPublic,
} from '@shared/api/proctoring'
import { usersApi } from '@shared/api/users'
import { extractErrorMessage } from '@shared/api/client'
import type { AttemptPublic, Exam } from '@shared/types/exams'
import type { UserDetail } from '@shared/types/users'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

type Tab = 'events' | 'snapshots' | 'answers' | 'decision'

const examId = computed(() => Number(route.params.id))
const attemptId = computed(() => Number(route.params.attemptId))

const tab = ref<Tab>('events')

const exam = ref<Exam | null>(null)
const attempts = ref<AttemptPublic | null>(null)
const events = ref<ProctoringEventPublic[]>([])
const snapshots = ref<ProctoringSnapshotPublic[]>([])
const idRef = ref<IdReferencePhoto | null>(null)
const student = ref<UserDetail | null>(null)
// Phase 9e — answers tab uchun (plagiat ko'rsatish)
const attemptResult = ref<import('@shared/types/exams').AttemptResult | null>(null)

const loading = ref(true)
const error = ref<string | null>(null)
const acting = ref(false)
const actionMsg = ref<string | null>(null)
const decisionReason = ref('')

async function load() {
  loading.value = true
  error.value = null
  try {
    const [e, atts, evs, snaps, ref_, res] = await Promise.all([
      examsApi.get(examId.value),
      attemptsApi.listForExam(examId.value, { page_size: 100 }),
      proctoringApi.listEvents(attemptId.value),
      proctoringApi.listSnapshots(attemptId.value),
      proctoringApi.getIdReference(attemptId.value).catch(() => null),
      attemptsApi.result(attemptId.value).catch(() => null),
    ])
    exam.value = e
    attempts.value = atts.items.find((a) => a.id === attemptId.value) ?? null
    events.value = evs
    snapshots.value = snaps
    idRef.value = ref_
    attemptResult.value = res
    if (attempts.value) {
      try {
        student.value = await usersApi.get(attempts.value.user_id)
      } catch {
        student.value = null
      }
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

const eventsBySeverity = computed(() => {
  const out = { critical: 0, warning: 0, info: 0 }
  for (const e of events.value) out[e.severity]++
  return out
})

const reviewStatus = computed(() => {
  if (!attempts.value) return 'default' as const
  if (attempts.value.flagged) return 'warning' as const
  if (attempts.value.violation_score >= 40) return 'warning' as const
  return 'success' as const
})

async function handleInvalidate() {
  if (!decisionReason.value.trim()) {
    actionMsg.value = t('attempt_review.reason_required')
    return
  }
  const ok = await confirm({
    title: t('attempt_review.invalidate_confirm'),
    description: decisionReason.value.trim(),
    variant: 'danger',
    confirmLabel: t('attempt_review.invalidate'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  acting.value = true
  actionMsg.value = null
  try {
    await attemptsApi.invalidate(attemptId.value, decisionReason.value.trim())
    actionMsg.value = t('attempt_review.invalidated')
    toast.success(t('attempt_review.invalidated'))
    await load()
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.save_error'))
    actionMsg.value = msg
    toast.error(msg)
  } finally {
    acting.value = false
  }
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString()
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

function severityVariant(s: string): 'default' | 'warning' | 'danger' {
  if (s === 'critical') return 'danger'
  if (s === 'warning') return 'warning'
  return 'default'
}

// Phase 9f — smart score helpers
function smartScoreVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score >= 60) return 'danger'
  if (score >= 30) return 'warning'
  return 'success'
}

function smartRecommendationKey(score: number): string {
  if (score >= 60) return 'attempt_review.smart_recommended_invalidate'
  if (score >= 30) return 'attempt_review.smart_recommended_review'
  return 'attempt_review.smart_recommended_approve'
}

const KNOWN_FLAG_TYPES = new Set([
  'combo_paste_tab',
  'burst',
  'low_face_avg',
  'frequent_gaze_off',
  'identity_mismatch',
  'devtools',
])

function flagLabel(type: string): string {
  if (KNOWN_FLAG_TYPES.has(type)) return t(`attempt_review.smart_flag_${type}`)
  return type
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="space-y-6">
    <UiSkeleton :count="2" />
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
      <UiSkeleton v-for="i in 5" :key="i" height="h-20" />
    </div>
    <UiSkeleton variant="card" />
  </div>

  <UiAlert v-else-if="error" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="exam && attempts">
    <UiBreadcrumb
      :items="[
        t('dashboard.crumb_home'),
        t('exams.tab_exams'),
        exam.title,
        t('attempt_review.title'),
      ]"
      class="mb-6"
    />

    <div class="mb-6 flex items-start justify-between gap-4 flex-wrap">
      <div>
        <div class="flex items-center gap-2 mb-2 flex-wrap">
          <UiBadge variant="default">{{ t(`exams.type_${exam.type}`) }}</UiBadge>
          <UiBadge :variant="reviewStatus" with-dot>
            {{ t(`exam_result.status_${attempts.status}`) }}
          </UiBadge>
          <UiBadge v-if="attempts.flagged" variant="warning" with-dot>
            {{ t('attempt_review.flagged') }}
          </UiBadge>
        </div>
        <h1 class="page-title mb-1.5">{{ exam.title }}</h1>
        <p class="page-subtitle">
          <span v-if="student">{{ student.full_name }} · {{ student.email }} · </span>
          {{ t('exam_result.attempt_n', { n: attempts.attempt_number }) }}
        </p>
      </div>
      <UiButton variant="outline" @click="router.back()">
        ← {{ t('common.cancel') }}
      </UiButton>
    </div>

    <!-- Identity verification card -->
    <UiCard class="mb-6" no-padding>
      <div class="p-4 border-b border-border">
        <div class="text-[13px] font-semibold">
          {{ t('attempt_review.identity_section') }}
        </div>
        <div class="text-[11px] text-muted-foreground mt-0.5">
          {{ t('attempt_review.identity_hint') }}
        </div>
      </div>
      <div class="p-4 grid grid-cols-1 md:grid-cols-[200px_1fr] gap-4 items-start">
        <!-- ID reference photo -->
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-1.5">
            {{ t('attempt_review.id_reference') }}
          </div>
          <div class="aspect-square bg-muted/30 rounded-md overflow-hidden border border-border">
            <a v-if="idRef" :href="idRef.url" target="_blank" rel="noopener">
              <img
                :src="idRef.url"
                :alt="t('attempt_review.id_reference')"
                class="w-full h-full object-cover"
              />
            </a>
            <div
              v-else
              class="w-full h-full grid place-items-center text-[12px] text-muted-foreground text-center px-2"
            >
              {{ t('attempt_review.no_id_reference') }}
            </div>
          </div>
          <div v-if="student" class="mt-2 text-[12px]">
            <div class="font-semibold">{{ student.full_name }}</div>
            <div class="font-mono text-[11px] text-muted-foreground">
              {{ student.email }}
            </div>
            <div v-if="student.phone" class="font-mono text-[11px] text-muted-foreground">
              {{ student.phone }}
            </div>
          </div>
        </div>

        <!-- Snapshots strip preview -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
              {{ t('attempt_review.snapshots_preview') }}
            </div>
            <div class="text-[11px] font-mono text-muted-foreground">
              {{ snapshots.length }} {{ t('exam_take.snapshots_n', { n: snapshots.length }).split(' ').slice(1).join(' ') }}
            </div>
          </div>
          <div
            v-if="snapshots.length === 0"
            class="aspect-[4/1] rounded-md border border-dashed border-border grid place-items-center text-[12px] text-muted-foreground"
          >
            {{ t('attempt_review.no_snapshots') }}
          </div>
          <div
            v-else
            class="grid grid-cols-4 sm:grid-cols-6 lg:grid-cols-8 gap-1.5"
          >
            <a
              v-for="s in snapshots.slice(0, 8)"
              :key="s.id"
              :href="s.url"
              target="_blank"
              rel="noopener"
              class="aspect-square block bg-black rounded overflow-hidden border border-border hover:border-foreground transition-colors relative"
            >
              <img
                :src="s.url"
                :alt="`Snapshot ${s.id}`"
                class="w-full h-full object-cover"
                loading="lazy"
              />
              <span
                v-if="s.face_count !== null && s.face_count !== 1"
                class="absolute top-0.5 right-0.5 px-1 bg-warning-500 text-white text-[9px] font-mono rounded"
              >
                {{ s.face_count }}
              </span>
            </a>
          </div>
        </div>
      </div>
    </UiCard>

    <!-- Score summary -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
      <UiStatCard
        :label="t('attempt_review.kpi_total_score')"
        :value="`${attempts.total_score ?? '—'} / ${attempts.max_score ?? '—'}`"
      />
      <UiStatCard
        :label="t('attempt_review.kpi_percentage')"
        :value="`${attempts.percentage ?? '—'}%`"
      />
      <UiStatCard
        :label="t('attempt_review.kpi_violation_score')"
        :value="String(attempts.violation_score)"
      />
      <UiStatCard
        :label="t('attempt_review.kpi_smart_score')"
        :value="String(attempts.smart_score ?? 0)"
      />
      <UiStatCard
        :label="t('attempt_review.kpi_events')"
        :value="String(events.length)"
      />
    </div>

    <!-- Phase 9f — Smart anomaly score -->
    <UiCard class="mb-6" no-padding>
      <div class="p-4 border-b border-border flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div class="text-[13px] font-semibold">
            {{ t('attempt_review.smart_section_title') }}
          </div>
          <div class="text-[11px] text-muted-foreground mt-0.5">
            {{ t('attempt_review.smart_section_hint') }}
          </div>
        </div>
        <UiBadge :variant="smartScoreVariant(attempts.smart_score ?? 0)" with-dot>
          {{ t(smartRecommendationKey(attempts.smart_score ?? 0)) }}
        </UiBadge>
      </div>
      <div class="p-4 grid grid-cols-1 md:grid-cols-[160px_1fr] gap-4 items-start">
        <!-- Gauge: numeric + horizontal bar -->
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-1.5">
            {{ t('attempt_review.kpi_smart_score') }}
          </div>
          <div
            class="text-[40px] font-mono font-semibold leading-none"
            :class="
              (attempts.smart_score ?? 0) >= 60
                ? 'text-danger-500'
                : (attempts.smart_score ?? 0) >= 30
                  ? 'text-warning-500'
                  : 'text-success-500'
            "
          >
            {{ attempts.smart_score ?? 0 }}
            <span class="text-[14px] text-muted-foreground font-normal">/ 100</span>
          </div>
          <div class="mt-2 h-2 rounded-full bg-muted overflow-hidden">
            <div
              class="h-full transition-all"
              :class="
                (attempts.smart_score ?? 0) >= 60
                  ? 'bg-danger-500'
                  : (attempts.smart_score ?? 0) >= 30
                    ? 'bg-warning-500'
                    : 'bg-success-500'
              "
              :style="{ width: `${Math.min(100, attempts.smart_score ?? 0)}%` }"
            ></div>
          </div>
        </div>
        <!-- Flags list -->
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-1.5">
            {{ t('attempt_review.tab_events') }}
          </div>
          <div
            v-if="!attempts.smart_flags || attempts.smart_flags.length === 0"
            class="text-[12px] text-muted-foreground py-2"
          >
            {{ t('attempt_review.smart_no_flags') }}
          </div>
          <ul v-else class="space-y-1.5">
            <li
              v-for="(f, idx) in attempts.smart_flags"
              :key="idx"
              class="flex items-start gap-2.5 text-[12px]"
            >
              <span
                class="mt-0.5 font-mono text-[10px] px-1.5 py-0.5 rounded shrink-0"
                :class="
                  f.weight >= 30
                    ? 'bg-danger-500/15 text-danger-600'
                    : f.weight >= 15
                      ? 'bg-warning-500/15 text-warning-600'
                      : 'bg-muted text-muted-foreground'
                "
              >
                +{{ f.weight }}
              </span>
              <div class="min-w-0">
                <div class="font-medium">{{ flagLabel(f.type) }}</div>
                <div class="text-[11px] font-mono text-muted-foreground truncate">
                  {{ f.detail }}
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </UiCard>

    <UiTabs
      v-model="tab"
      :tabs="[
        { id: 'events', label: t('attempt_review.tab_events') },
        { id: 'snapshots', label: t('attempt_review.tab_snapshots') },
        { id: 'answers', label: t('attempt_review.tab_answers') },
        { id: 'decision', label: t('attempt_review.tab_decision') },
      ]"
    />

    <!-- Events tab -->
    <div v-if="tab === 'events'" class="mt-4">
      <div class="flex flex-wrap gap-3 mb-4 text-[12px] font-mono text-muted-foreground">
        <span>● {{ t('attempt_review.severity_critical') }}: {{ eventsBySeverity.critical }}</span>
        <span>● {{ t('attempt_review.severity_warning') }}: {{ eventsBySeverity.warning }}</span>
        <span>● {{ t('attempt_review.severity_info') }}: {{ eventsBySeverity.info }}</span>
      </div>

      <UiEmptyState
        v-if="events.length === 0"
        :title="t('attempt_review.no_events')"
      />


      <UiCard v-else no-padding>
        <ul class="divide-y divide-border">
          <li
            v-for="e in events"
            :key="e.id"
            class="px-4 py-2.5 flex items-center gap-3 hover:bg-muted/30"
          >
            <span class="font-mono text-[11px] text-muted-foreground w-20 shrink-0">
              {{ fmtTime(e.occurred_at) }}
            </span>
            <UiBadge :variant="severityVariant(e.severity)" with-dot>
              {{ t(`proctoring.severity_${e.severity}`) }}
            </UiBadge>
            <span class="text-[13px]">{{ t(`proctoring.event_${e.event_type}`) }}</span>
            <span
              v-if="e.event_metadata"
              class="text-[11px] font-mono text-muted-foreground truncate ml-auto"
            >
              {{ JSON.stringify(e.event_metadata) }}
            </span>
          </li>
        </ul>
      </UiCard>
    </div>

    <!-- Snapshots tab -->
    <div v-if="tab === 'snapshots'" class="mt-4">
      <UiEmptyState
        v-if="snapshots.length === 0"
        :title="t('attempt_review.no_snapshots')"
      />

      <div
        v-else
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2"
      >
        <a
          v-for="s in snapshots"
          :key="s.id"
          :href="s.url"
          target="_blank"
          rel="noopener"
          class="block aspect-video bg-black rounded-md overflow-hidden border border-border hover:border-foreground transition-colors relative group"
        >
          <img
            :src="s.url"
            :alt="`Snapshot ${s.id}`"
            class="w-full h-full object-cover"
            loading="lazy"
          />
          <div
            class="absolute bottom-0 left-0 right-0 px-2 py-1 bg-black/70 text-[10px] font-mono text-white opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <div>{{ fmtTime(s.captured_at) }}</div>
            <div v-if="s.face_count !== null">
              <span :class="s.face_count !== 1 ? 'text-warning-400' : 'text-success-400'">
                {{ s.face_count }} face(s)
              </span>
            </div>
            <div v-if="s.face_match_score !== null && s.face_match_score !== undefined">
              <span
                :class="
                  Number(s.face_match_score) < 0.4
                    ? 'text-danger-400'
                    : Number(s.face_match_score) < 0.6
                      ? 'text-warning-400'
                      : 'text-success-400'
                "
              >
                match: {{ (Number(s.face_match_score) * 100).toFixed(0) }}%
              </span>
            </div>
          </div>
          <!-- Always-visible badges (top-right) -->
          <span
            v-if="s.face_count !== null && s.face_count !== 1"
            class="absolute top-0.5 right-0.5 px-1 bg-warning-500 text-white text-[9px] font-mono rounded"
          >
            {{ s.face_count }}f
          </span>
          <span
            v-else-if="s.face_match_score !== null && s.face_match_score !== undefined && Number(s.face_match_score) < 0.4"
            class="absolute top-0.5 right-0.5 px-1 bg-danger-500 text-white text-[9px] font-mono rounded"
          >
            ⚠ {{ (Number(s.face_match_score) * 100).toFixed(0) }}%
          </span>
        </a>
      </div>
    </div>

    <!-- Phase 9e — Answers tab (plagiat score per answer) -->
    <div v-if="tab === 'answers'" class="mt-4">
      <UiEmptyState
        v-if="!attemptResult || attemptResult.answers.length === 0"
        :title="t('attempt_review.no_answers')"
      />

      <div v-else class="space-y-3">
        <UiCard
          v-for="(a, idx) in attemptResult.answers"
          :key="a.id"
          no-padding
        >
          <div class="p-4">
            <div class="flex items-baseline gap-3 mb-2 flex-wrap">
              <span class="font-mono text-[12px] text-muted-foreground">#{{ idx + 1 }}</span>
              <UiBadge
                v-if="a.auto_correct === true"
                variant="success"
                with-dot
              >
                {{ t('exam_result.correct') }}
              </UiBadge>
              <UiBadge
                v-else-if="a.auto_correct === false"
                variant="warning"
                with-dot
              >
                {{ t('exam_result.wrong') }}
              </UiBadge>
              <UiBadge v-else variant="default" with-dot>
                {{ t('exam_result.manual_grading') }}
              </UiBadge>
              <UiBadge
                v-if="a.plagiarism_score !== null && Number(a.plagiarism_score) >= 30"
                :variant="
                  Number(a.plagiarism_score) >= 60
                    ? 'danger'
                    : 'warning'
                "
                with-dot
                :title="
                  a.plagiarism_match_answer_id
                    ? t('attempt_review.plagiarism_match', { id: a.plagiarism_match_answer_id })
                    : ''
                "
              >
                {{ t('exam_result.plagiarism_badge', { pct: Number(a.plagiarism_score).toFixed(0) }) }}
              </UiBadge>
              <span class="font-mono text-[12px] text-muted-foreground ml-auto">
                {{ a.points_earned }} / {{ a.points_max ?? '—' }}
              </span>
            </div>
            <div
              v-if="a.text_answer"
              class="text-[13px] text-foreground whitespace-pre-wrap"
            >
              {{ a.text_answer }}
            </div>
            <pre
              v-if="a.code_answer"
              class="text-[12px] font-mono text-foreground bg-muted/40 rounded p-2 overflow-x-auto whitespace-pre"
            >{{ a.code_answer }}</pre>
            <div v-if="a.file_url" class="text-[12px] font-mono text-muted-foreground">
              📎 {{ a.file_url }}
            </div>
          </div>
        </UiCard>
      </div>
    </div>

    <!-- Decision tab -->
    <div v-if="tab === 'decision'" class="mt-4">
      <UiAlert
        v-if="actionMsg"
        :variant="actionMsg.startsWith('Error') ? 'danger' : 'info'"
        class="mb-4"
      >
        {{ actionMsg }}
      </UiAlert>

      <UiCard>
        <div class="text-[13px] mb-3">
          {{ t('attempt_review.decision_intro') }}
        </div>

        <ul class="text-[12px] text-muted-foreground space-y-1 list-disc pl-5 mb-4">
          <li v-if="attempts.violation_score >= 80">
            ⚠️ {{ t('attempt_review.decision_high_score') }}
          </li>
          <li v-else-if="attempts.violation_score >= 40">
            ⚠️ {{ t('attempt_review.decision_medium_score') }}
          </li>
          <li v-else>✓ {{ t('attempt_review.decision_low_score') }}</li>
        </ul>

        <label class="block text-[13px] font-medium mb-1">
          {{ t('attempt_review.reason_label') }}
        </label>
        <textarea
          v-model="decisionReason"
          rows="3"
          :placeholder="t('attempt_review.reason_placeholder')"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus mb-3"
        ></textarea>

        <div class="flex gap-2">
          <UiButton
            variant="outline"
            :disabled="attempts.status === 'invalidated' || acting"
            :loading="acting"
            class="text-danger-600 border-danger-500"
            @click="handleInvalidate"
          >
            {{ t('attempt_review.invalidate') }}
          </UiButton>
          <UiButton
            variant="ghost"
            @click="router.push({ name: 'course-builder', params: { id: exam.course_id } })"
          >
            {{ t('attempt_review.back_to_exam') }}
          </UiButton>
        </div>

        <div class="text-[11px] font-mono text-muted-foreground mt-4">
          {{ t('attempt_review.created_at') }}: {{ fmtDateTime(attempts.created_at) }}
          ·
          {{ t('attempt_review.updated_at') }}: {{ fmtDateTime(attempts.updated_at) }}
        </div>
      </UiCard>
    </div>
  </template>
</template>
