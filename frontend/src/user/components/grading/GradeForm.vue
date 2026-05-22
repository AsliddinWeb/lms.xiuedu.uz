<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { submissionsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type {
  Assignment,
  GradeLetter,
  GradePayload,
  Rubric,
  Submission,
} from '@shared/types/assignments'

interface Props {
  submission: Submission
  assignment: Assignment
  rubric: Rubric | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ graded: [submission: Submission] }>()

const { t } = useI18n()

type Mode = 'score' | 'rubric'
const mode = ref<Mode>('score')
const score = ref<number | ''>('')
const rubricScores = ref<Record<string, number>>({})
const letter = ref<GradeLetter | ''>('')
const feedback = ref('')
const returnForRevision = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const successMsg = ref<string | null>(null)

const letterOptions = [
  { value: '', label: t('grade_form.letter_none') },
  { value: 'A', label: 'A' },
  { value: 'B', label: 'B' },
  { value: 'C', label: 'C' },
  { value: 'D', label: 'D' },
  { value: 'F', label: 'F' },
]

const rubricTotal = computed(() => {
  let sum = 0
  for (const v of Object.values(rubricScores.value)) {
    if (typeof v === 'number' && !Number.isNaN(v)) sum += v
  }
  return sum
})

watch(
  () => [props.submission, props.rubric, props.assignment],
  () => {
    error.value = null
    successMsg.value = null
    score.value = props.submission.score === null ? '' : Number(props.submission.score)
    letter.value = (props.submission.grade_letter as GradeLetter) ?? ''
    feedback.value = props.submission.feedback ?? ''
    returnForRevision.value = props.submission.status === 'returned'

    if (props.rubric) {
      const initial: Record<string, number> = {}
      for (const c of props.rubric.criteria) {
        const existing = (props.submission.rubric_scores as Record<string, number>)[c.key]
        initial[c.key] = typeof existing === 'number' ? existing : 0
      }
      rubricScores.value = initial
      mode.value = 'rubric'
    } else {
      rubricScores.value = {}
      mode.value = 'score'
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  error.value = null
  successMsg.value = null
  submitting.value = true
  try {
    const payload: GradePayload = {
      feedback: feedback.value.trim() || null,
      return_for_revision: returnForRevision.value,
    }
    if (letter.value) payload.grade_letter = letter.value as GradeLetter
    if (mode.value === 'rubric' && props.rubric) {
      payload.rubric_scores = { ...rubricScores.value }
    } else {
      payload.score = score.value === '' ? undefined : Number(score.value)
    }
    const updated = await submissionsApi.grade(props.submission.id, payload)
    successMsg.value = t('grade_form.saved')
    emit('graded', updated)
  } catch (e) {
    error.value = extractErrorMessage(e, 'Saqlashda xato')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="border border-border rounded-lg p-5 bg-background">
    <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-3">
      {{ t('grade_form.title') }}
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-3">{{ error }}</UiAlert>
    <UiAlert v-if="successMsg" variant="success" class="mb-3">{{ successMsg }}</UiAlert>

    <!-- Mode tabs (only if rubric attached) -->
    <div v-if="rubric" class="mb-4 flex gap-1 border-b border-border">
      <button
        v-for="opt in (['rubric', 'score'] as Mode[])"
        :key="opt"
        type="button"
        class="px-3 py-2 text-[12px] font-medium border-b-2 -mb-px transition-colors"
        :class="
          mode === opt
            ? 'border-foreground text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        "
        @click="mode = opt"
      >
        {{ t(`grade_form.mode_${opt}`) }}
      </button>
    </div>

    <UiAlert v-else variant="neutral" class="mb-4">
      {{ t('grade_form.no_rubric') }}
    </UiAlert>

    <form @submit.prevent="handleSubmit">
      <!-- Direct score mode -->
      <template v-if="mode === 'score' || !rubric">
        <UiFormField :label="t('grade_form.score_label')" required>
          <UiInput
            v-model="score"
            type="number"
            :min="0"
            :max="Number(assignment.max_score)"
            step="0.5"
            required
          />
          <div class="text-[11px] font-mono text-muted-foreground mt-1">
            max {{ assignment.max_score }}
          </div>
        </UiFormField>
      </template>

      <!-- Rubric mode -->
      <template v-else-if="rubric">
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
                class="w-24 rounded-md border border-border-strong bg-background text-foreground text-[13px] text-right px-2 py-1.5 outline-none focus:border-foreground focus:shadow-focus font-mono"
              />
            </div>
          </div>
          <div class="mt-3 pt-3 border-t border-border flex items-center justify-between text-[13px]">
            <span class="font-mono text-[11px] uppercase text-muted-foreground">
              {{ t('grade_form.rubric_total_label', { value: rubricTotal }) }}
            </span>
            <span class="font-mono text-[11px] text-muted-foreground">
              / {{ rubric.total_points }}
            </span>
          </div>
        </div>
      </template>

      <UiFormField :label="t('grade_form.letter_label')">
        <UiSelect v-model="letter" :options="letterOptions" />
      </UiFormField>

      <UiFormField :label="t('grade_form.feedback_label')">
        <textarea
          v-model="feedback"
          rows="4"
          :placeholder="t('grade_form.feedback_placeholder')"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <label class="flex items-start gap-2 cursor-pointer text-[13px] mb-4">
        <input
          v-model="returnForRevision"
          type="checkbox"
          class="w-3.5 h-3.5 mt-1 accent-foreground"
        />
        <span>
          <span class="font-medium">{{ t('grade_form.return_for_revision') }}</span>
          <span class="block text-[11px] text-muted-foreground mt-0.5 leading-4">
            {{ t('grade_form.return_help') }}
          </span>
        </span>
      </label>

      <div class="flex justify-end">
        <UiButton type="submit" :loading="submitting">
          {{ t('grade_form.submit') }}
        </UiButton>
      </div>
    </form>
  </div>
</template>
