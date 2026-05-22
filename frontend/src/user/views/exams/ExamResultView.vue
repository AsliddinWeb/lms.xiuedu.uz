<script setup lang="ts">
/**
 * Phase 6e — Exam result view.
 *
 * Talaba submitdan keyin shu sahifaga keladi: yakuniy ball, foiz, statusi.
 * Agar exam.show_correct_answers=true bo'lsa, har savol bo'yicha tahlil
 * ko'rsatiladi (correct/wrong + to'g'ri javob).
 */

import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { attemptsApi, examsApi } from '@shared/api/exams'
import { extractErrorMessage } from '@shared/api/client'
import type { AttemptResult, Exam } from '@shared/types/exams'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const examId = computed(() => Number(route.params.id))
const attemptId = computed(() => Number(route.params.attemptId))

const exam = ref<Exam | null>(null)
const result = ref<AttemptResult | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    const [e, r] = await Promise.all([
      examsApi.get(examId.value),
      attemptsApi.result(attemptId.value),
    ])
    exam.value = e
    result.value = r
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

const statusVariant = computed(() => {
  if (!result.value) return 'default'
  if (result.value.passed) return 'success'
  if (result.value.passed === false) return 'warning'
  return 'default'
})

const minutesSpent = computed(() => {
  if (!result.value) return 0
  return Math.round((result.value.time_spent_seconds / 60) * 10) / 10
})

const showAnswers = computed(() => result.value && result.value.answers.length > 0)

onMounted(load)
</script>

<template>
  <div v-if="loading" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="exam && result">
    <UiBreadcrumb
      :items="[t('dashboard.crumb_home'), t('exams.tab_exams'), exam.title]"
      class="mb-6"
    />

    <div class="mb-6">
      <div class="flex items-center gap-2 mb-2 flex-wrap">
        <UiBadge :variant="statusVariant" with-dot>
          {{ t(`exam_result.status_${result.status}`) }}
        </UiBadge>
        <UiBadge
          v-if="result.passed === true"
          variant="success"
        >
          {{ t('exam_result.passed') }}
        </UiBadge>
        <UiBadge
          v-else-if="result.passed === false"
          variant="warning"
        >
          {{ t('exam_result.failed') }}
        </UiBadge>
      </div>
      <h1 class="page-title mb-1.5">{{ exam.title }}</h1>
      <p class="page-subtitle">
        {{ t('exam_result.attempt_n', { n: result.attempt_number }) }}
      </p>
    </div>

    <!-- Score summary -->
    <UiCard class="mb-6">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            {{ t('exam_result.total_score') }}
          </div>
          <div class="text-2xl font-semibold mt-1 font-mono">
            {{ result.total_score ?? '—' }}
            <span class="text-[14px] text-muted-foreground">
              / {{ result.max_score ?? '—' }}
            </span>
          </div>
        </div>
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            {{ t('exam_result.percentage') }}
          </div>
          <div class="text-2xl font-semibold mt-1 font-mono">
            {{ result.percentage ?? '—' }}%
          </div>
        </div>
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            {{ t('exam_result.auto_score') }}
          </div>
          <div class="text-2xl font-semibold mt-1 font-mono">
            {{ result.auto_score ?? '—' }}
          </div>
        </div>
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            {{ t('exam_result.time_spent') }}
          </div>
          <div class="text-2xl font-semibold mt-1 font-mono">
            {{ minutesSpent }} {{ t('exam_lobby.minutes') }}
          </div>
        </div>
      </div>
    </UiCard>

    <UiAlert
      v-if="result.manual_score === null && result.status !== 'graded'"
      variant="info"
      class="mb-6"
    >
      {{ t('exam_result.manual_pending') }}
    </UiAlert>

    <!-- Per-question breakdown (if show_correct_answers) -->
    <div v-if="showAnswers" class="space-y-3">
      <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
        {{ t('exam_result.answers_breakdown') }}
      </div>

      <UiCard
        v-for="(a, idx) in result.answers"
        :key="a.id"
        no-padding
      >
        <div class="p-4">
          <div class="flex items-baseline gap-3 mb-2">
            <span class="font-mono text-[12px] text-muted-foreground">
              #{{ idx + 1 }}
            </span>
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
            <!-- Phase 9e — plagiat badge -->
            <UiBadge
              v-if="a.plagiarism_score !== null && Number(a.plagiarism_score) >= 30"
              :variant="
                Number(a.plagiarism_score) >= 60
                  ? 'danger'
                  : Number(a.plagiarism_score) >= 30
                    ? 'warning'
                    : 'default'
              "
              with-dot
              :title="t('exam_result.plagiarism_tooltip')"
            >
              {{ t('exam_result.plagiarism_badge', { pct: Number(a.plagiarism_score).toFixed(0) }) }}
            </UiBadge>
            <span class="font-mono text-[12px] text-muted-foreground ml-auto">
              {{ a.points_earned }} / {{ a.points_max ?? '—' }}
            </span>
          </div>
          <div
            v-if="a.text_answer"
            class="text-[13px] text-muted-foreground whitespace-pre-wrap mb-1"
          >
            {{ a.text_answer }}
          </div>
          <div
            v-if="a.code_answer"
            class="text-[12px] font-mono text-muted-foreground bg-muted/50 rounded p-2 whitespace-pre-wrap"
          >
            {{ a.code_answer }}
          </div>
          <div
            v-if="a.file_url"
            class="text-[12px] font-mono text-muted-foreground"
          >
            📎 {{ a.file_url }}
          </div>
          <div
            v-if="a.grader_comment"
            class="text-[12px] text-foreground bg-info-500/10 rounded p-2 mt-2"
          >
            <span class="font-semibold">{{ t('exam_result.grader_comment') }}:</span>
            {{ a.grader_comment }}
          </div>
        </div>
      </UiCard>
    </div>

    <div class="mt-8 flex gap-2">
      <UiButton variant="outline" @click="router.replace({ name: 'dashboard' })">
        {{ t('exam_result.back_to_dashboard') }}
      </UiButton>
    </div>
  </template>
</template>
