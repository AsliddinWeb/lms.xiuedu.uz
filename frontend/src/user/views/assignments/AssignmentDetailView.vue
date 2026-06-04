<script setup lang="ts">
import { computed, onMounted, ref, toRef, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { appealsApi, assignmentsApi, rubricsApi } from '@shared/api/assignments'
import { coursesApi } from '@shared/api/courses'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { useDueCountdown } from '@shared/composables/useDueCountdown'
import type { Appeal, Assignment, Rubric, Submission } from '@shared/types/assignments'
import type { Course } from '@shared/types/courses'

import AssignmentSubmitForm from '@user/components/assignments/AssignmentSubmitForm.vue'
import GradeFeedbackCard from '@user/components/assignments/GradeFeedbackCard.vue'
import SubmissionsTimeline from '@user/components/assignments/SubmissionsTimeline.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const assignmentId = computed(() => Number(route.params.id))

const assignment = ref<Assignment | null>(null)
const course = ref<Course | null>(null)
const rubric = ref<Rubric | null>(null)
const submissions = ref<Submission[]>([])
const myAppeals = ref<Appeal[]>([])

const latestAppealForLatest = computed<Appeal | null>(() => {
  if (submissions.value.length === 0) return null
  const sid = submissions.value[0].id
  return myAppeals.value.find((a) => a.submission_id === sid) ?? null
})

const loading = ref(false)
const error = ref<string | null>(null)

const latest = computed<Submission | null>(() =>
  submissions.value.length > 0 ? submissions.value[0] : null,
)

const attemptsUsed = computed(() => submissions.value.length)
const attemptsLeft = computed(() =>
  assignment.value
    ? Math.max(0, assignment.value.max_attempts - attemptsUsed.value)
    : 0,
)

const { label: dueLabel, isOverdue } = useDueCountdown(
  toRef(() => assignment.value?.due_date ?? null),
)

const submitDisabledReason = computed(() => {
  if (!assignment.value) return null
  // Pending attempt — submit blocked
  if (latest.value && (latest.value.status === 'submitted' || latest.value.status === 'grading')) {
    return t('assignments.submit_warning_pending')
  }
  if (attemptsLeft.value === 0) return t('assignments.submit_warning_no_attempts')
  if (
    isOverdue.value &&
    !assignment.value.late_submission_allowed
  ) {
    return t('assignments.submit_warning_late_blocked')
  }
  // closed_at o'tgan
  if (
    assignment.value.closed_at &&
    new Date(assignment.value.closed_at).getTime() < Date.now()
  ) {
    return t('assignments.submit_warning_late_blocked')
  }
  return null
})

const showLatePenaltyHint = computed(
  () =>
    isOverdue.value &&
    !!assignment.value?.late_submission_allowed &&
    Number(assignment.value.late_penalty_per_day) > 0,
)

async function load() {
  loading.value = true
  error.value = null
  try {
    assignment.value = await assignmentsApi.get(assignmentId.value)
    const [subs, courseData, appeals] = await Promise.all([
      assignmentsApi.listMySubmissions(assignmentId.value),
      coursesApi.get(assignment.value.course_id).catch(() => null),
      appealsApi.listMine().catch(() => [] as Appeal[]),
    ])
    submissions.value = subs
    course.value = courseData
    myAppeals.value = appeals
    if (assignment.value.rubric_id) {
      rubric.value = await rubricsApi
        .get(assignment.value.rubric_id)
        .catch(() => null)
    } else {
      rubric.value = null
    }
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'my-assignments' })
      return
    }
    error.value = extractErrorMessage(e, 'Yuklashda xato')
  } finally {
    loading.value = false
  }
}

function onAppealCreated(ap: Appeal) {
  myAppeals.value = [ap, ...myAppeals.value]
}

onMounted(load)

watch(assignmentId, load)

function onSubmitted(s: Submission) {
  // Yangi attempt timeline boshiga qo'shamiz
  submissions.value = [s, ...submissions.value]
}
</script>

<template>
  <div v-if="loading && !assignment" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !assignment" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="assignment">
    <!-- Breadcrumb -->
    <UiBreadcrumb
      :items="[
        t('dashboard.crumb_home'),
        t('my_assignments.tab_all'),
        assignment.title,
      ]"
      class="mb-6"
    />

    <!-- Page header -->
    <div class="mb-6">
      <div class="flex items-center gap-2 mb-2 flex-wrap">
        <UiBadge variant="default">
          {{ t(`assignments.type_${assignment.type}`) }}
        </UiBadge>
        <UiBadge :variant="isOverdue ? 'danger' : 'default'" :with-dot="isOverdue">
          {{ dueLabel }}
        </UiBadge>
        <RouterLink
          v-if="course"
          :to="{ name: 'course-detail', params: { id: course.id } }"
          class="font-mono text-[11px] text-muted-foreground hover:text-foreground hover:underline"
        >
          · {{ course.title }}
        </RouterLink>
      </div>
      <h1 class="page-title mb-1.5 truncate">{{ assignment.title }}</h1>
      <p
        v-if="assignment.description"
        class="page-subtitle line-clamp-3"
      >
        {{ assignment.description }}
      </p>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <UiAlert
      v-if="showLatePenaltyHint && !submitDisabledReason"
      variant="warning"
      class="mb-4"
    >
      {{ t('assignments.submit_warning_late_penalty', { pct: assignment.late_penalty_per_day }) }}
    </UiAlert>

    <!-- 3-col stat strip -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
      <div class="border border-border rounded-md p-3 bg-card">
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('assignments.due_label') }}
        </div>
        <div class="text-[13px] font-medium mt-1">{{ dueLabel }}</div>
      </div>
      <div class="border border-border rounded-md p-3 bg-card">
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('assignments.max_score_label') }}
        </div>
        <div class="text-[13px] font-medium mt-1 font-mono tabular-nums">
          {{ assignment.max_score }}
        </div>
      </div>
      <div class="border border-border rounded-md p-3 bg-card">
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('assignments.attempts_label') }}
        </div>
        <div class="text-[13px] font-medium mt-1 font-mono tabular-nums">
          {{ t('assignments.attempts_value', {
            used: attemptsUsed,
            max: assignment.max_attempts,
          }) }}
        </div>
      </div>
    </div>

    <!-- 2-col grid: main + sidebar (rubric + instructions context) -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
      <!-- Main column -->
      <div class="min-w-0 space-y-6">
        <!-- Instructions -->
        <UiCard v-if="assignment.instructions" no-padding>
          <div class="px-5 py-3 border-b border-border">
            <span class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {{ t('assignment_detail.instructions') }}
            </span>
          </div>
          <p class="text-[13px] leading-6 whitespace-pre-wrap text-foreground px-5 py-4">
            {{ assignment.instructions }}
          </p>
        </UiCard>

        <!-- Latest grade card (if available) -->
        <GradeFeedbackCard
          v-if="latest && (latest.status === 'graded' || latest.status === 'returned')"
          :submission="latest"
          :rubric="rubric"
          :max-score="assignment.max_score"
          :can-appeal="true"
          :my-appeal="latestAppealForLatest"
          @appeal-created="onAppealCreated"
        />

        <!-- Submit form -->
        <AssignmentSubmitForm
          :assignment="assignment"
          :disabled-reason="submitDisabledReason"
          @submitted="onSubmitted"
        />

        <!-- History -->
        <SubmissionsTimeline :submissions="submissions" />
      </div>

      <!-- Sidebar: rubric + tips -->
      <aside class="space-y-4">
        <UiCard v-if="rubric" no-padding>
          <div class="px-5 py-3 border-b border-border flex items-center justify-between">
            <span class="text-[13px] font-semibold">{{ t('assignments.rubric_section') }}</span>
            <span class="font-mono text-[11px] text-muted-foreground">
              {{ t('assignments.rubric_total', { n: rubric.total_points }) }}
            </span>
          </div>
          <div class="px-5 py-3 space-y-2">
            <div
              v-for="c in rubric.criteria"
              :key="c.key"
              class="flex items-center gap-3 text-[13px] py-1.5 border-b border-border last:border-b-0"
            >
              <span class="flex-1 truncate">{{ c.name }}</span>
              <span class="font-mono text-[11px] text-muted-foreground shrink-0">
                max {{ c.max_points }}
              </span>
            </div>
          </div>
        </UiCard>

        <!-- Peer review (Phase 21.2) — agar topshiriqda yoqilgan bo'lsa -->
        <UiCard v-if="assignment.peer_review_enabled" no-padding>
          <div class="px-5 py-3 border-b border-border">
            <span class="text-[13px] font-semibold">{{ t('assignment_detail.peer_review_title') }}</span>
          </div>
          <div class="px-5 py-3 space-y-2.5">
            <p class="text-[12px] text-muted-foreground leading-relaxed">
              {{ t('assignment_detail.peer_review_info', { n: assignment.peer_reviews_per_submission }) }}
            </p>
            <UiButton
              variant="outline"
              size="sm"
              class="w-full justify-center"
              @click="router.push({ name: 'my-peer-reviews' })"
            >
              {{ t('assignment_detail.peer_review_cta') }} →
            </UiButton>
          </div>
        </UiCard>

        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border">
            <span class="text-[13px] font-semibold">{{ t('assignment_detail.tips_title') }}</span>
          </div>
          <ul class="px-5 py-3 text-[12px] text-muted-foreground space-y-2 list-disc list-inside">
            <li>{{ t('assignment_detail.tip_attempts') }}</li>
            <li v-if="assignment.late_submission_allowed">
              {{ t('assignment_detail.tip_late_allowed', { pct: assignment.late_penalty_per_day }) }}
            </li>
            <li v-else>{{ t('assignment_detail.tip_late_blocked') }}</li>
            <li>{{ t('assignment_detail.tip_save_draft') }}</li>
          </ul>
        </UiCard>
      </aside>
    </div>
  </template>
</template>
