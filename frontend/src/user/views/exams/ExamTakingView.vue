<script setup lang="ts">
/**
 * Phase 6e — Exam taking shell.
 *
 * Fullscreen shell (sidebar'siz layout). Anti-cheat:
 *  - Tab visibility (visibilitychange) — violation count + ogohlantirish
 *  - Copy/paste/contextmenu block
 *  - Fullscreen lock (allow_tab_switch=false bo'lsa)
 *  - Auto-save: javob o'zgarganda debounced + har 30 sek periodic
 *  - Timer countdown — oxirgi 5 daqiqada qizil; 0 bo'lganda auto-submit
 *
 * Layout:
 *  ┌─[Timer]─[Q i/n]──────────────────[Submit]─┐
 *  │ Sidebar (Q list) │ Current question        │
 *  │                  │ [← Prev] [Next →]       │
 *  └──[Status ●Online ●REC]────────────────────┘
 */

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import { attemptsApi } from '@shared/api/exams'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import type { AnswerSubmit, AttemptTakeView } from '@shared/types/exams'

import { useProctoring } from '@user/composables/useProctoring'
import QuestionRenderer from '@user/components/exams/QuestionRenderer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const examId = computed(() => Number(route.params.id))
const attemptId = computed(() => Number(route.params.attemptId))

const attempt = ref<AttemptTakeView | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const submitting = ref(false)

const currentIdx = ref(0)
const answers = ref<Map<number, AnswerSubmit>>(new Map())
const savingQuestionId = ref<number | null>(null)
const saveError = ref<string | null>(null)

// Anti-cheat
const violations = ref(0)
const violationMsg = ref<string | null>(null)
const allowTabSwitch = ref(false)

// Proctoring engine (camera + events)
// Phase 9a — sessionStorage'dan lobby reference face descriptor'ni o'qiymiz
function loadFaceRef(): Float32Array | null {
  try {
    const raw = sessionStorage.getItem(`exam_face_ref_${examId.value}`)
    if (!raw) return null
    return Float32Array.from(JSON.parse(raw) as number[])
  } catch {
    return null
  }
}

const proctor = useProctoring({
  attemptId: attemptId.value,
  faceReferenceDescriptor: loadFaceRef(),
})
const proctorVideoRef = ref<HTMLVideoElement | null>(null)

// Timer
const now = ref(Date.now())
let nowTimer: ReturnType<typeof setInterval> | null = null
let periodicSaveTimer: ReturnType<typeof setInterval> | null = null

const currentQuestion = computed(() =>
  attempt.value ? attempt.value.questions[currentIdx.value] ?? null : null,
)
const totalQuestions = computed(() => attempt.value?.questions.length ?? 0)

function emptyAnswer(qid: number): AnswerSubmit {
  return {
    question_id: qid,
    selected_option_ids: null,
    text_answer: null,
    code_answer: null,
    file_url: null,
    file_size_bytes: null,
  }
}

function isAnswered(a: AnswerSubmit | undefined): boolean {
  if (!a) return false
  if (a.selected_option_ids && a.selected_option_ids.length > 0) return true
  if (a.text_answer && a.text_answer.trim()) return true
  if (a.code_answer && a.code_answer.trim()) return true
  if (a.file_url) return true
  return false
}

const answeredCount = computed(() => {
  let n = 0
  for (const a of answers.value.values()) {
    if (isAnswered(a)) n++
  }
  return n
})

const remainingSec = computed(() => {
  if (!attempt.value) return 0
  const end = new Date(attempt.value.deadline_at).getTime()
  return Math.max(0, Math.floor((end - now.value) / 1000))
})

const timerLabel = computed(() => {
  const s = remainingSec.value
  const m = Math.floor(s / 60)
  const ss = s % 60
  return `${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
})

const timerCritical = computed(() => remainingSec.value > 0 && remainingSec.value <= 5 * 60)
const timerExpired = computed(() => remainingSec.value === 0)

const currentAnswer = computed<AnswerSubmit>(() => {
  const q = currentQuestion.value
  if (!q) return emptyAnswer(0)
  return answers.value.get(q.id) ?? emptyAnswer(q.id)
})

// ---------- Load attempt ----------

async function loadAttempt() {
  loading.value = true
  error.value = null
  try {
    const data = await attemptsApi.get(attemptId.value)
    attempt.value = data
    // Saqlangan javoblarni Map'ga yuklash
    const map = new Map<number, AnswerSubmit>()
    for (const sa of data.saved_answers) {
      map.set(sa.question_id, sa)
    }
    answers.value = map
    // Birinchi javobsiz savolga o'tish
    const firstUnanswered = data.questions.findIndex((q) => !isAnswered(map.get(q.id)))
    currentIdx.value = firstUnanswered >= 0 ? firstUnanswered : 0
    // Status submit bo'lib qolgan bo'lsa, result'ga
    if (data.status !== 'in_progress') {
      router.replace({
        name: 'exam-result',
        params: { id: String(examId.value), attemptId: String(attemptId.value) },
      })
      return
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

// ---------- Auto-save ----------

const saveTimers = new Map<number, ReturnType<typeof setTimeout>>()

function onAnswerUpdate(updated: AnswerSubmit) {
  const qid = updated.question_id
  answers.value.set(qid, updated)
  // Debounce: 800ms tinch turganda saqlash
  const prev = saveTimers.get(qid)
  if (prev) clearTimeout(prev)
  saveTimers.set(
    qid,
    setTimeout(() => persistAnswer(qid), 800),
  )
}

async function persistAnswer(qid: number) {
  const a = answers.value.get(qid)
  if (!a || !attempt.value) return
  if (attempt.value.status !== 'in_progress') return
  savingQuestionId.value = qid
  saveError.value = null
  try {
    await attemptsApi.saveAnswer(attemptId.value, a)
  } catch (e) {
    saveError.value = extractErrorMessage(e, t('exam_take.save_error'))
  } finally {
    savingQuestionId.value = null
  }
}

async function flushAll() {
  // Periodic ham, submit oldidan ham — barcha javoblarni serverga yuborish
  const promises: Promise<unknown>[] = []
  for (const a of answers.value.values()) {
    if (isAnswered(a)) {
      promises.push(attemptsApi.saveAnswer(attemptId.value, a).catch(() => null))
    }
  }
  await Promise.all(promises)
}

// ---------- Navigation ----------

function gotoQuestion(idx: number) {
  if (!attempt.value) return
  if (idx < 0 || idx >= attempt.value.questions.length) return
  currentIdx.value = idx
}
function gotoPrev() {
  gotoQuestion(currentIdx.value - 1)
}
function gotoNext() {
  gotoQuestion(currentIdx.value + 1)
}

// ---------- Submit ----------

async function handleSubmit(auto = false) {
  if (!attempt.value || submitting.value) return
  if (!auto) {
    const unanswered = totalQuestions.value - answeredCount.value
    const msg =
      unanswered > 0
        ? t('exam_take.submit_confirm_with_unanswered', { n: unanswered })
        : t('exam_take.submit_confirm')
    const ok = await confirm({
      title: msg,
      variant: unanswered > 0 ? 'danger' : 'default',
      confirmLabel: t('exam_take.submit'),
      cancelLabel: t('common.cancel'),
    })
    if (!ok) return
  }
  submitting.value = true
  try {
    await flushAll()
    await attemptsApi.submit(attemptId.value)
    // Anti-cheat to'xtatish + redirect
    teardownAntiCheat()
    proctor.stop()
    router.replace({
      name: 'exam-result',
      params: { id: String(examId.value), attemptId: String(attemptId.value) },
    })
  } catch (e) {
    error.value = extractErrorMessage(e, t('exam_take.submit_error'))
  } finally {
    submitting.value = false
  }
}

// ---------- Anti-cheat ----------

function recordViolation(
  reason: string,
  eventType: string,
  severity: 'info' | 'warning' | 'critical' = 'warning',
  metadata: Record<string, unknown> | null = null,
) {
  violations.value++
  violationMsg.value = reason
  proctor.reportEvent(eventType, severity, metadata).catch(() => null)
}

function onVisibilityChange() {
  if (document.visibilityState === 'hidden' && !allowTabSwitch.value) {
    recordViolation(
      t('exam_take.violation_tab_switch'),
      'visibility_lost',
      'warning',
    )
  } else if (document.visibilityState === 'visible') {
    proctor.reportEvent('visibility_returned', 'info').catch(() => null)
  }
}
function blockCopy(e: ClipboardEvent) {
  e.preventDefault()
  recordViolation(t('exam_take.violation_copy'), 'copy_attempt', 'info')
}
function blockPaste(e: ClipboardEvent) {
  e.preventDefault()
  recordViolation(t('exam_take.violation_paste'), 'paste_attempt', 'warning')
}
function blockContextMenu(e: MouseEvent) {
  e.preventDefault()
  proctor.reportEvent('context_menu', 'info').catch(() => null)
}
function onFullscreenChange() {
  if (allowTabSwitch.value) return
  if (!document.fullscreenElement) {
    recordViolation(
      t('exam_take.violation_fullscreen_exit'),
      'fullscreen_exit',
      'warning',
    )
  } else {
    proctor.reportEvent('fullscreen_entered', 'info').catch(() => null)
  }
}
async function enterFullscreen() {
  try {
    await document.documentElement.requestFullscreen()
  } catch {
    // Brauzer ruxsat bermasligi mumkin — silent
  }
}
function setupAntiCheat() {
  document.addEventListener('visibilitychange', onVisibilityChange)
  document.addEventListener('copy', blockCopy)
  document.addEventListener('paste', blockPaste)
  document.addEventListener('contextmenu', blockContextMenu)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  if (!allowTabSwitch.value) {
    enterFullscreen()
  }
}
function teardownAntiCheat() {
  document.removeEventListener('visibilitychange', onVisibilityChange)
  document.removeEventListener('copy', blockCopy)
  document.removeEventListener('paste', blockPaste)
  document.removeEventListener('contextmenu', blockContextMenu)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {})
  }
}

// ---------- Lifecycle ----------

watch(timerExpired, async (expired) => {
  if (expired && attempt.value?.status === 'in_progress' && !submitting.value) {
    await handleSubmit(true)
  }
})

onMounted(async () => {
  await loadAttempt()
  if (!attempt.value) return

  // allow_tab_switch flag attempt orqali yo'q — exam'dan keladi. Backend
  // AttemptTakeView'da bu bayroq yo'q, default false (qattiq). Plan'da 6e da
  // exam'dan olish kerak — endpoint'ga qo'shamiz keyinroq. Hozir false default.
  allowTabSwitch.value = false

  setupAntiCheat()

  // Proctoring kamera + 30s snapshot loop
  if (proctorVideoRef.value) {
    proctor.start(proctorVideoRef.value).catch(() => null)
  }

  nowTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)

  periodicSaveTimer = setInterval(() => {
    flushAll().catch(() => null)
  }, 30000)
})

onBeforeUnmount(() => {
  if (nowTimer) clearInterval(nowTimer)
  if (periodicSaveTimer) clearInterval(periodicSaveTimer)
  for (const t of saveTimers.values()) clearTimeout(t)
  saveTimers.clear()
  teardownAntiCheat()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground">
    <!-- Top bar -->
    <header
      class="flex items-center gap-4 px-5 py-3 border-b border-border bg-card sticky top-0 z-20"
    >
      <div
        class="font-mono text-[18px] font-semibold tabular-nums px-3 py-1 rounded-md"
        :class="timerCritical ? 'bg-danger-500/15 text-danger-600' : 'bg-muted'"
      >
        {{ timerLabel }}
      </div>

      <div class="text-[12px] font-mono text-muted-foreground">
        {{ t('exam_take.question_n_of_m', { n: currentIdx + 1, m: totalQuestions }) }}
      </div>

      <div class="flex-1 flex justify-center gap-2">
        <UiBadge v-if="savingQuestionId !== null" variant="default">
          {{ t('exam_take.saving') }}
        </UiBadge>
        <UiBadge v-if="violations > 0" variant="warning" with-dot>
          {{ t('exam_take.violations_n', { n: violations }) }}
        </UiBadge>
      </div>

      <UiButton :loading="submitting" :disabled="!attempt" @click="handleSubmit(false)">
        {{ t('exam_take.submit') }}
      </UiButton>
    </header>

    <!-- Violation toast -->
    <UiAlert
      v-if="violationMsg"
      variant="warning"
      class="m-4"
    >
      <div class="flex items-center justify-between gap-4">
        <span>{{ violationMsg }}</span>
        <button
          type="button"
          class="text-[11px] font-mono text-muted-foreground hover:text-foreground"
          @click="violationMsg = null"
        >
          ×
        </button>
      </div>
    </UiAlert>

    <UiAlert v-if="error" variant="danger" class="m-4">{{ error }}</UiAlert>
    <UiAlert v-if="saveError" variant="warning" class="m-4">{{ saveError }}</UiAlert>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 grid place-items-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>

    <!-- Main -->
    <main
      v-else-if="attempt && currentQuestion"
      class="flex-1 grid grid-cols-[200px_1fr] min-h-0"
    >
      <!-- Sidebar: question navigation -->
      <aside class="border-r border-border bg-card overflow-y-auto">
        <div class="p-3 border-b border-border">
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            {{ t('exam_take.questions') }}
          </div>
          <div class="text-[12px] text-muted-foreground mt-0.5">
            {{ answeredCount }}/{{ totalQuestions }} {{ t('exam_take.answered') }}
          </div>
        </div>
        <ul class="p-2 space-y-1">
          <li v-for="(q, idx) in attempt.questions" :key="q.id">
            <button
              type="button"
              class="w-full text-left px-2.5 py-1.5 rounded-md text-[13px] flex items-center gap-2 transition-colors"
              :class="
                currentIdx === idx
                  ? 'bg-foreground text-background'
                  : 'hover:bg-muted text-foreground'
              "
              @click="gotoQuestion(idx)"
            >
              <span
                class="inline-block w-4 h-4 grid place-items-center text-[10px] font-mono shrink-0"
              >
                <span v-if="isAnswered(answers.get(q.id))" class="text-success-500">●</span>
                <span v-else class="text-muted-foreground">○</span>
              </span>
              <span class="font-mono text-[12px]">{{ idx + 1 }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <!-- Question content -->
      <section class="overflow-y-auto">
        <div class="max-w-3xl mx-auto px-6 py-8">
          <QuestionRenderer
            :question="currentQuestion"
            :model-value="currentAnswer"
            :attempt-id="attemptId"
            @update:model-value="onAnswerUpdate"
          />

          <div class="flex items-center justify-between mt-8 pt-4 border-t border-border">
            <UiButton
              variant="outline"
              :disabled="currentIdx === 0"
              @click="gotoPrev"
            >
              ← {{ t('exam_take.prev') }}
            </UiButton>
            <UiButton
              variant="outline"
              :disabled="currentIdx >= totalQuestions - 1"
              @click="gotoNext"
            >
              {{ t('exam_take.next') }} →
            </UiButton>
          </div>
        </div>
      </section>
    </main>

    <!-- Bottom status bar -->
    <footer
      class="flex items-center gap-3 px-5 py-2 border-t border-border bg-card text-[11px] font-mono text-muted-foreground"
    >
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-success-500"></span>
        {{ t('exam_take.status_online') }}
      </span>
      <span v-if="!allowTabSwitch" class="flex items-center gap-1.5">
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-danger-500 animate-pulse"></span>
        {{ t('exam_take.status_monitored') }}
      </span>
      <span class="ml-auto flex items-center gap-3">
        <span>{{ t('exam_take.snapshots_n', { n: proctor.snapshotsUploaded.value }) }}</span>
        <span>{{ t('exam_take.events_n', { n: proctor.eventsSent.value }) }}</span>
      </span>
    </footer>

    <!-- Proctoring camera widget (bottom-right) -->
    <div
      v-show="!loading && attempt"
      class="fixed bottom-12 right-4 z-30 w-40 h-30 rounded-md overflow-hidden border-2 border-danger-500/70 bg-black shadow-lg"
    >
      <video
        ref="proctorVideoRef"
        autoplay
        muted
        playsinline
        class="w-full h-full object-cover"
      ></video>
      <div
        class="absolute top-1 left-1 px-1.5 py-0.5 bg-danger-500 text-[10px] font-mono text-white rounded flex items-center gap-1"
      >
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
        REC
      </div>
    </div>
  </div>
</template>
