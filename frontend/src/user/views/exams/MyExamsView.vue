<script setup lang="ts">
/**
 * Talaba uchun imtihonlar ro'yxati — yozilgan kurslardagi published imtihonlar.
 * Har imtihon kartochkasida: kurs, turi, davomiyligi, savollar soni,
 * urinishlar holati va "Boshlash"/"Davom etish"/"Natija" tugmasi.
 */

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import { attemptsApi, examsApi } from '@shared/api/exams'
import { extractErrorMessage } from '@shared/api/client'
import type { AttemptStudentSummary, Exam } from '@shared/types/exams'

const { t } = useI18n()
const router = useRouter()

const exams = ref<Exam[]>([])
const attemptsByExam = ref<Record<number, AttemptStudentSummary[]>>({})
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await examsApi.my({ page_size: 100 })
    exams.value = data.items
    const map: Record<number, AttemptStudentSummary[]> = {}
    await Promise.all(
      data.items.map(async (e) => {
        try {
          map[e.id] = await attemptsApi.myAttempts(e.id)
        } catch {
          map[e.id] = []
        }
      }),
    )
    attemptsByExam.value = map
  } catch (e) {
    console.error('[MyExamsView] load failed:', e)
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

function attemptInfo(examId: number) {
  const list = attemptsByExam.value[examId] ?? []
  const inProgress = list.find((a) => a.status === 'in_progress')
  const submittedOrGraded = list
    .filter((a) => ['submitted', 'auto_submitted', 'graded'].includes(a.status))
    .sort((a, b) => b.attempt_number - a.attempt_number)[0]
  return { list, inProgress, latest: submittedOrGraded }
}

function startOrResume(exam: Exam) {
  const info = attemptInfo(exam.id)
  if (info.inProgress) {
    router.push({
      name: 'exam-take',
      params: { id: String(exam.id), attemptId: String(info.inProgress.id) },
    })
  } else {
    router.push({ name: 'exam-lobby', params: { id: String(exam.id) } })
  }
}

function openResult(exam: Exam, attemptId: number) {
  router.push({
    name: 'exam-result',
    params: { id: String(exam.id), attemptId: String(attemptId) },
  })
}

function canStartMore(exam: Exam, examId: number): boolean {
  const used = (attemptsByExam.value[examId] ?? []).filter(
    (a) =>
      ['submitted', 'auto_submitted', 'graded', 'in_progress'].includes(a.status),
  ).length
  return used < exam.max_attempts
}

const todaysExams = computed(() => exams.value)

onMounted(load)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('my_exams.title')]"
    class="mb-6"
  />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('my_exams.title') }}</h1>
    <p class="page-subtitle">{{ t('my_exams.subtitle') }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-2 gap-3">
    <UiSkeleton v-for="i in 4" :key="i" variant="card" />
  </div>

  <UiEmptyState
    v-else-if="todaysExams.length === 0"
    :title="t('my_exams.empty')"
    :description="t('my_exams.subtitle')"
  />


  <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
    <UiCard v-for="ex in todaysExams" :key="ex.id">
      <template #header>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1 flex-wrap">
            <UiBadge variant="default">{{ t(`exams.type_${ex.type}`) }}</UiBadge>
            <UiBadge v-if="ex.proctoring_enabled" variant="warning" with-dot>
              {{ t('exam_lobby.proctoring_required') }}
            </UiBadge>
            <UiBadge
              v-if="attemptInfo(ex.id).inProgress"
              variant="warning"
            >
              {{ t('my_exams.in_progress') }}
            </UiBadge>
            <UiBadge
              v-else-if="attemptInfo(ex.id).latest?.passed === true"
              variant="success"
              with-dot
            >
              {{ t('exam_result.passed') }}
            </UiBadge>
            <UiBadge
              v-else-if="attemptInfo(ex.id).latest?.passed === false"
              variant="default"
              with-dot
            >
              {{ t('exam_result.failed') }}
            </UiBadge>
          </div>
          <h3 class="text-base font-semibold text-foreground truncate">
            {{ ex.title }}
          </h3>
        </div>
      </template>

      <div class="flex flex-wrap gap-3 text-[11px] font-mono text-muted-foreground mb-3">
        <span>{{ ex.duration_minutes }} {{ t('exam_lobby.minutes') }}</span>
        <span>{{ ex.total_questions }} q</span>
        <span>{{ ex.total_points }} pts</span>
        <span>pass: {{ ex.passing_score }}%</span>
        <span>
          {{ t('my_exams.attempts_used', {
            n: attemptInfo(ex.id).list.length,
            max: ex.max_attempts,
          }) }}
        </span>
      </div>

      <p v-if="ex.description" class="text-[13px] text-muted-foreground line-clamp-2 mb-2">
        {{ ex.description }}
      </p>

      <template #actions>
        <div class="flex flex-wrap gap-1.5">
          <UiButton
            v-if="attemptInfo(ex.id).inProgress"
            size="sm"
            @click="startOrResume(ex)"
          >
            {{ t('my_exams.resume') }} →
          </UiButton>
          <UiButton
            v-else-if="canStartMore(ex, ex.id)"
            size="sm"
            @click="startOrResume(ex)"
          >
            {{ t('my_exams.start') }} →
          </UiButton>
          <UiButton
            v-else
            size="sm"
            variant="ghost"
            disabled
          >
            {{ t('my_exams.no_attempts_left') }}
          </UiButton>
          <UiButton
            v-if="attemptInfo(ex.id).latest"
            variant="outline"
            size="sm"
            @click="openResult(ex, attemptInfo(ex.id).latest!.id)"
          >
            {{ t('my_exams.view_result') }}
          </UiButton>
        </div>
      </template>
    </UiCard>
  </div>
</template>
