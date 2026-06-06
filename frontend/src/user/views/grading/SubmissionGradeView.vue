<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { assignmentsApi, rubricsApi, submissionsApi } from '@shared/api/assignments'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import type {
  Assignment,
  Rubric,
  Submission,
} from '@shared/types/assignments'

import PlagiarismBadge from '@user/components/assignments/PlagiarismBadge.vue'
import GradeForm from '@user/components/grading/GradeForm.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const submissionId = computed(() => Number(route.params.id))

const submission = ref<Submission | null>(null)
const assignment = ref<Assignment | null>(null)
const rubric = ref<Rubric | null>(null)

const studentName = computed(() =>
  submission.value?.user_full_name ?? (submission.value ? `#${submission.value.user_id}` : null),
)

// Inline annotations (full-replace PUT semantics)
const annotations = ref<{ text: string; color?: string }[]>([])
const newAnnotation = ref('')
const savingAnnotations = ref(false)
const annotationsMsg = ref<string | null>(null)

const loading = ref(false)
const error = ref<string | null>(null)
const checkingPlagiarism = ref(false)

async function runPlagiarismCheck() {
  if (!submission.value) return
  checkingPlagiarism.value = true
  try {
    const result = await submissionsApi.checkPlagiarism(submission.value.id)
    submission.value = {
      ...submission.value,
      plagiarism_score: result.plagiarism_score,
      plagiarism_report_url: result.plagiarism_report_url,
      plagiarism_flagged: result.plagiarism_flagged,
      plagiarism_checked_at: result.plagiarism_checked_at,
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    checkingPlagiarism.value = false
  }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    submission.value = await submissionsApi.get(submissionId.value)
    assignment.value = await assignmentsApi.get(submission.value.assignment_id)

    if (assignment.value.rubric_id) {
      rubric.value = await rubricsApi
        .get(assignment.value.rubric_id)
        .catch(() => null)
    } else {
      rubric.value = null
    }

    // Annotations: server'da {text, color, ...} JSONB sifatida saqlanadi
    annotations.value = (submission.value.annotations as Array<{ text: string; color?: string }>)
      .map((a) => ({ text: a.text ?? '', color: a.color }))
      .filter((a) => a.text)
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'grading-inbox' })
      return
    }
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(submissionId, load)

async function persistAnnotations() {
  if (!submission.value) return
  savingAnnotations.value = true
  annotationsMsg.value = null
  try {
    const updated = await submissionsApi.saveAnnotations(
      submission.value.id,
      annotations.value.map((a) => ({ text: a.text, color: a.color })),
    )
    submission.value = updated
    annotationsMsg.value = t('grade_form.saved')
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    savingAnnotations.value = false
  }
}

async function addAnnotation() {
  const text = newAnnotation.value.trim()
  if (!text) return
  annotations.value = [...annotations.value, { text }]
  newAnnotation.value = ''
  await persistAnnotations()
}

async function removeAnnotation(idx: number) {
  annotations.value = annotations.value.filter((_, i) => i !== idx)
  await persistAnnotations()
}

function fmtDateTime(s: string): string {
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function onGraded(updated: Submission) {
  submission.value = updated
  // Baholangach inbox'ga qaytamiz — pedagog keyingi ishga o'tadi
  toast.success(t('grade_form.saved'))
  router.push({ name: 'grading-inbox' })
}
</script>

<template>
  <div v-if="loading && !submission" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !submission" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="submission && assignment">
    <UiBreadcrumb
      :items="[t('dashboard.crumb_home'), t('grading_inbox.title'), assignment.title]"
      class="mb-3"
    />
    <button
      type="button"
      class="inline-flex items-center gap-1.5 mb-5 text-[12px] font-mono text-muted-foreground hover:text-foreground transition-colors"
      @click="router.push({ name: 'grading-inbox' })"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m15 18-6-6 6-6" />
      </svg>
      {{ t('grading_inbox.back_to_inbox') }}
    </button>
    <!-- Header -->
    <div class="mb-6">
      <div class="flex items-end justify-between gap-6">
        <div class="min-w-0">
          <div class="flex items-center gap-2 mb-2 flex-wrap">
            <UiBadge variant="default">{{ t(`assignments.type_${assignment.type}`) }}</UiBadge>
            <UiBadge
              :variant="
                submission.status === 'graded'
                  ? 'success'
                  : submission.status === 'returned'
                    ? 'warning'
                    : 'default'
              "
              with-dot
            >
              {{ t(`assignments.status_${submission.status}`) }}
            </UiBadge>
            <UiBadge v-if="submission.is_late" variant="warning">
              {{ t('assignments.days_late_label', { n: submission.days_late }) }}
            </UiBadge>
            <PlagiarismBadge
              v-if="submission.plagiarism_checked_at"
              :score="submission.plagiarism_score"
              :flagged="submission.plagiarism_flagged"
              :report-url="submission.plagiarism_report_url"
            />
            <UiButton
              v-if="assignment.plagiarism_check_enabled"
              variant="outline"
              size="sm"
              :loading="checkingPlagiarism"
              @click="runPlagiarismCheck"
            >
              {{ submission.plagiarism_checked_at ? t('plagiarism.run_check') : t('plagiarism.run_check') }}
            </UiButton>
          </div>
          <h1 class="page-title mb-1.5 truncate">{{ assignment.title }}</h1>
          <div class="page-subtitle">
            {{ studentName }}
            <span class="text-muted-foreground"> · {{ t('grading_inbox.col_attempt') }} #{{ submission.attempt_number }} · </span>
            {{ fmtDateTime(submission.submitted_at) }}
            <RouterLink
              :to="{ name: 'course-builder', params: { id: assignment.course_id } }"
              class="ml-2 font-mono text-[11px] text-muted-foreground hover:text-foreground hover:underline"
            >
              ↗ course
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <!-- 2-col layout -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-5">
      <!-- LEFT: submission content -->
      <div class="space-y-4">
        <UiCard>
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            {{ t('grade_form.submission_section') }}
          </div>
          <p
            v-if="submission.content"
            class="text-[13.5px] leading-7 whitespace-pre-wrap text-foreground"
          >
            {{ submission.content }}
          </p>
          <p v-else class="text-[13px] text-muted-foreground italic">
            {{ t('grade_form.no_content') }}
          </p>
        </UiCard>

        <UiCard>
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            {{ t('grade_form.files_section') }}
          </div>
          <div
            v-if="submission.files.length === 0"
            class="text-[13px] text-muted-foreground italic"
          >
            {{ t('grade_form.no_files') }}
          </div>
          <ul v-else class="space-y-1.5">
            <li v-for="(f, i) in submission.files" :key="i">
              <a
                :href="f.url"
                target="_blank"
                rel="noopener noreferrer"
                class="flex items-center gap-2 text-[13px] hover:underline"
              >
                <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor"
                  stroke-width="1.5" stroke-linecap="round" class="text-muted-foreground">
                  <path d="M3 3h7l5 5v7a2 2 0 0 1-2 2H3z" />
                  <path d="M10 3v5h5" />
                </svg>
                <span class="font-medium">{{ f.name }}</span>
                <span class="font-mono text-[10px] text-muted-foreground">
                  {{ fmtSize(f.size) }}
                </span>
              </a>
            </li>
          </ul>
        </UiCard>

        <!-- Annotations -->
        <UiCard>
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            {{ t('grade_form.annotations_section') }}
          </div>
          <p class="text-[11px] text-muted-foreground mb-3">
            {{ t('grade_form.annotations_help') }}
          </p>

          <ul v-if="annotations.length > 0" class="space-y-2 mb-3">
            <li
              v-for="(a, i) in annotations"
              :key="i"
              class="flex items-start gap-2 px-3 py-2 border border-border rounded-md"
            >
              <span class="flex-1 text-[13px] leading-5">{{ a.text }}</span>
              <UiButton
                variant="ghost"
                size="sm"
                class="text-danger-600 shrink-0"
                @click="removeAnnotation(i)"
              >
                {{ t('grade_form.annotation_remove') }}
              </UiButton>
            </li>
          </ul>

          <div class="flex items-center gap-2">
            <input
              v-model="newAnnotation"
              type="text"
              :placeholder="t('grade_form.annotation_placeholder')"
              class="flex-1 rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
              @keydown.enter.prevent="addAnnotation"
            />
            <UiButton
              variant="outline"
              size="sm"
              :loading="savingAnnotations"
              :disabled="!newAnnotation.trim()"
              @click="addAnnotation"
            >
              +
            </UiButton>
          </div>
          <p
            v-if="annotationsMsg"
            class="text-[11px] text-success-600 mt-2"
          >
            ✓ {{ annotationsMsg }}
          </p>
        </UiCard>
      </div>

      <!-- RIGHT: grade form -->
      <div class="lg:sticky lg:top-24 lg:self-start">
        <GradeForm
          :submission="submission"
          :assignment="assignment"
          :rubric="rubric"
          @graded="onGraded"
        />
      </div>
    </div>
  </template>
</template>
