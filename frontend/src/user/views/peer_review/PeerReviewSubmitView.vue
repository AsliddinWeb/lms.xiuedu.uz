<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import {
  assignmentsApi,
  peerReviewsApi,
  rubricsApi,
  submissionsApi,
} from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type {
  Assignment,
  PeerReview,
  PeerReviewSubmitPayload,
  Rubric,
  Submission,
} from '@shared/types/assignments'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const peerReviewId = computed(() => Number(route.params.id))

const submission = ref<Submission | null>(null)
const assignment = ref<Assignment | null>(null)
const rubric = ref<Rubric | null>(null)
const peerReview = ref<PeerReview | null>(null)

const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)

const score = ref<number | ''>('')
const rubricScores = ref<Record<string, number>>({})
const feedback = ref('')

const rubricTotal = computed(() => {
  let s = 0
  for (const v of Object.values(rubricScores.value)) {
    if (typeof v === 'number' && !Number.isNaN(v)) s += v
  }
  return s
})

async function load() {
  loading.value = true
  error.value = null
  try {
    // Talaba o'z peer_reviewlarini olib, ushbu id bo'yicha topadi
    const all = await peerReviewsApi.listMine(false)
    const pr = all.find((p) => p.id === peerReviewId.value)
    if (!pr) throw new Error(t('peer_review.not_found'))
    peerReview.value = pr

    const sub = await submissionsApi.get(pr.submission_id)
    submission.value = sub

    const a = await assignmentsApi.get(sub.assignment_id)
    assignment.value = a
    if (a.rubric_id) {
      rubric.value = await rubricsApi.get(a.rubric_id).catch(() => null)
    }

    // Initial values from existing peer review (if previously saved partial)
    if (pr.submitted_at) {
      score.value = pr.score ? Number(pr.score) : ''
      feedback.value = pr.feedback ?? ''
      rubricScores.value = (pr.rubric_scores ?? {}) as Record<string, number>
    } else if (rubric.value) {
      const init: Record<string, number> = {}
      for (const c of rubric.value.criteria) init[c.key] = 0
      rubricScores.value = init
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function handleSubmit() {
  if (!peerReview.value || peerReview.value.submitted_at) return
  error.value = null
  submitting.value = true
  try {
    const payload: PeerReviewSubmitPayload = {
      feedback: feedback.value.trim() || null,
    }
    if (rubric.value) {
      payload.rubric_scores = { ...rubricScores.value }
    } else {
      if (score.value === '') {
        error.value = t('peer_review.score_required')
        return
      }
      payload.score = Number(score.value)
    }
    await peerReviewsApi.submit(peerReview.value.id, payload)
    router.push({ name: 'my-peer-reviews' })
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div v-if="loading && !submission" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !submission" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="submission && assignment && peerReview">
    <UiBreadcrumb
      :items="[t('dashboard.crumb_home'), t('peer_review.title'), assignment.title]"
      class="mb-6"
    />
    <div class="mb-6">
      <h1 class="page-title mb-1.5">{{ assignment.title }}</h1>
      <UiAlert variant="neutral" class="mt-2">{{ t('peer_review.anon_note') }}</UiAlert>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-5">
      <!-- LEFT: anonim submission -->
      <div class="space-y-4">
        <UiCard>
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            {{ t('peer_review.submission_section') }}
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

          <div v-if="submission.files.length > 0" class="mt-4 pt-4 border-t border-border">
            <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
              {{ t('grade_form.files_section') }}
            </div>
            <ul class="space-y-1.5">
              <li v-for="(f, i) in submission.files" :key="i">
                <a
                  :href="f.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center gap-2 text-[13px] hover:underline"
                >
                  <span class="font-medium">{{ f.name }}</span>
                  <span class="font-mono text-[10px] text-muted-foreground">
                    {{ fmtSize(f.size) }}
                  </span>
                </a>
              </li>
            </ul>
          </div>
        </UiCard>
      </div>

      <!-- RIGHT: review form -->
      <div class="lg:sticky lg:top-24 lg:self-start">
        <div class="border border-border rounded-lg p-5 bg-background">
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-3">
            {{ t('peer_review.tag') }}
          </div>

          <UiBadge v-if="peerReview.submitted_at" variant="success" with-dot class="mb-3">
            {{ t('assignments.status_graded') }}
          </UiBadge>

          <form @submit.prevent="handleSubmit">
            <template v-if="rubric">
              <div class="mb-3">
                <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                  {{ t('grade_form.rubric_label') }}
                </div>
                <div class="space-y-2.5">
                  <div
                    v-for="c in rubric.criteria"
                    :key="c.key"
                    class="flex items-center gap-3"
                  >
                    <div class="flex-1 min-w-0">
                      <div class="text-[13px] font-medium text-foreground truncate">
                        {{ c.name }}
                      </div>
                      <div class="font-mono text-[10px] text-muted-foreground">
                        {{ t('grade_form.max_label', { n: c.max_points }) }}
                      </div>
                    </div>
                    <input
                      v-model.number="rubricScores[c.key]"
                      type="number"
                      min="0"
                      :max="Number(c.max_points)"
                      step="0.5"
                      :disabled="!!peerReview.submitted_at"
                      class="w-20 rounded-md border border-border-strong bg-background text-foreground text-[13px] text-right px-2 py-1.5 outline-none focus:border-foreground focus:shadow-focus font-mono disabled:opacity-60"
                    />
                  </div>
                </div>
                <div class="mt-3 pt-3 border-t border-border flex items-center justify-between text-[12px]">
                  <span class="font-mono text-[11px] uppercase text-muted-foreground">
                    {{ t('grade_form.rubric_total_label', { value: rubricTotal }) }}
                  </span>
                  <span class="font-mono text-[11px] text-muted-foreground">
                    / {{ rubric.total_points }}
                  </span>
                </div>
              </div>
            </template>

            <UiFormField v-else :label="t('peer_review.score_label', { max: assignment.max_score })" required>
              <UiInput
                v-model="score"
                type="number"
                min="0"
                :max="Number(assignment.max_score)"
                step="0.5"
                :disabled="!!peerReview.submitted_at"
                required
              />
            </UiFormField>

            <UiFormField :label="t('peer_review.feedback_section')">
              <textarea
                v-model="feedback"
                rows="4"
                :placeholder="t('peer_review.feedback_placeholder')"
                :disabled="!!peerReview.submitted_at"
                class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus disabled:opacity-60"
              ></textarea>
            </UiFormField>

            <div class="flex justify-end">
              <UiButton
                type="submit"
                :loading="submitting"
                :disabled="!!peerReview.submitted_at"
              >
                {{ t('peer_review.submit') }}
              </UiButton>
            </div>
          </form>
        </div>
      </div>
    </div>
  </template>
</template>
