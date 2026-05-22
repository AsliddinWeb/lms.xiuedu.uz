<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { codeTestCasesApi, questionsApi } from '@shared/api/exams'
import { extractErrorMessage } from '@shared/api/client'
import type {
  CodeTestCase,
  QuestionOptionPayload,
  QuestionPayload,
  QuestionPublic,
  QuestionType,
} from '@shared/types/exams'

interface Props {
  open: boolean
  examId: number
  question?: QuestionPublic | null
}
const props = withDefaults(defineProps<Props>(), { question: null })
const emit = defineEmits<{ close: []; saved: [q: QuestionPublic] }>()

const { t } = useI18n()

const type = ref<QuestionType>('single_choice')
const title = ref('')
const explanation = ref('')
const points = ref(1)
const required = ref(true)

// Options (single/multiple/true_false)
const options = ref<QuestionOptionPayload[]>([])

// short_text
const correctText = ref('')
const alternativeAnswers = ref('')
const exactMatch = ref(true)
const caseSensitive = ref(false)

// code
const codeLanguage = ref('')
const codeInitial = ref('')
// Phase 9d — test cases
interface DraftTestCase {
  id?: number
  stdin: string
  expected_stdout: string
  is_hidden: boolean
  weight: number
}
const codeTestCases = ref<DraftTestCase[]>([])
const loadingTestCases = ref(false)

async function loadTestCases(qid: number): Promise<void> {
  loadingTestCases.value = true
  try {
    const items: CodeTestCase[] = await codeTestCasesApi.list(qid)
    codeTestCases.value = items.map((i) => ({
      id: i.id,
      stdin: i.stdin,
      expected_stdout: i.expected_stdout,
      is_hidden: i.is_hidden,
      weight: Number(i.weight),
    }))
  } catch {
    codeTestCases.value = []
  } finally {
    loadingTestCases.value = false
  }
}

function addTestCase(): void {
  codeTestCases.value.push({
    stdin: '',
    expected_stdout: '',
    is_hidden: false,
    weight: 1,
  })
}

function removeTestCase(idx: number): void {
  codeTestCases.value.splice(idx, 1)
}

async function persistTestCases(questionId: number): Promise<void> {
  // Yangi qo'shilganlar va o'zgartirilganlarni saqlash
  for (const tc of codeTestCases.value) {
    if (!tc.expected_stdout.trim()) continue
    const payload = {
      stdin: tc.stdin,
      expected_stdout: tc.expected_stdout,
      is_hidden: tc.is_hidden,
      weight: tc.weight,
    }
    if (tc.id) {
      await codeTestCasesApi.update(tc.id, payload)
    } else {
      const created = await codeTestCasesApi.create(questionId, payload)
      tc.id = created.id
    }
  }
}

// file_upload
const maxFileSizeMb = ref<number | null>(null)
const allowedFileTypes = ref('')

const submitting = ref(false)
const errorMsg = ref<string | null>(null)

const typeOptions = computed(() => [
  { value: 'single_choice', label: t('exams.qtype_single_choice') },
  { value: 'multiple_choice', label: t('exams.qtype_multiple_choice') },
  { value: 'true_false', label: t('exams.qtype_true_false') },
  { value: 'short_text', label: t('exams.qtype_short_text') },
  { value: 'essay', label: t('exams.qtype_essay') },
  { value: 'code', label: t('exams.qtype_code') },
  { value: 'file_upload', label: t('exams.qtype_file_upload') },
])

const hasOptions = computed(() =>
  ['single_choice', 'multiple_choice', 'true_false'].includes(type.value),
)
const isShortText = computed(() => type.value === 'short_text')
const isCode = computed(() => type.value === 'code')
const isFileUpload = computed(() => type.value === 'file_upload')
const isManualOnly = computed(() => ['essay', 'code', 'file_upload'].includes(type.value))

function ensureMinOptions() {
  if (type.value === 'true_false') {
    options.value = [
      { text: t('exams.value_true'), is_correct: true, explanation: null, order_index: 0 },
      { text: t('exams.value_false'), is_correct: false, explanation: null, order_index: 1 },
    ]
    return
  }
  if (options.value.length < 2) {
    while (options.value.length < 2) {
      options.value.push({
        text: '',
        is_correct: false,
        explanation: null,
        order_index: options.value.length,
      })
    }
  }
}

watch(type, () => {
  if (hasOptions.value) ensureMinOptions()
})

function addOption() {
  options.value.push({
    text: '',
    is_correct: false,
    explanation: null,
    order_index: options.value.length,
  })
}

function removeOption(idx: number) {
  if (options.value.length <= 2) return
  options.value.splice(idx, 1)
  options.value.forEach((o, i) => (o.order_index = i))
}

function onSingleSelect(idx: number) {
  options.value.forEach((o, i) => (o.is_correct = i === idx))
}

function reset() {
  errorMsg.value = null
  if (props.question) {
    const q = props.question
    type.value = q.type
    title.value = q.title
    explanation.value = q.explanation ?? ''
    points.value = Number(q.points)
    required.value = q.required
    options.value = (q.options ?? []).map((o, i) => ({
      text: o.text,
      is_correct: o.is_correct,
      explanation: o.explanation ?? null,
      order_index: o.order_index ?? i,
    }))
    correctText.value = q.correct_text ?? ''
    alternativeAnswers.value = (q.alternative_answers ?? []).join('\n')
    exactMatch.value = q.exact_match
    caseSensitive.value = q.case_sensitive
    codeLanguage.value = q.code_language ?? ''
    codeInitial.value = q.code_initial ?? ''
    maxFileSizeMb.value = q.max_file_size_mb ?? null
    allowedFileTypes.value = (q.allowed_file_types ?? []).join(', ')
  } else {
    type.value = 'single_choice'
    title.value = ''
    explanation.value = ''
    points.value = 1
    required.value = true
    options.value = []
    correctText.value = ''
    alternativeAnswers.value = ''
    exactMatch.value = true
    caseSensitive.value = false
    codeLanguage.value = ''
    codeInitial.value = ''
    maxFileSizeMb.value = null
    allowedFileTypes.value = ''
    ensureMinOptions()
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      reset()
      codeTestCases.value = []
      // Existing code question — test caselarni yuklash
      if (props.question && props.question.type === 'code') {
        loadTestCases(props.question.id).catch(() => null)
      }
    }
  },
)

async function handleSubmit() {
  errorMsg.value = null

  if (hasOptions.value) {
    const filled = options.value.filter((o) => o.text.trim())
    if (filled.length < 2) {
      errorMsg.value = t('exams.validation_min_2_options')
      return
    }
    const correctCount = filled.filter((o) => o.is_correct).length
    if (type.value === 'single_choice' && correctCount !== 1) {
      errorMsg.value = t('exams.validation_single_choice_one_correct')
      return
    }
    if (type.value === 'multiple_choice' && correctCount < 1) {
      errorMsg.value = t('exams.validation_multi_choice_min_one_correct')
      return
    }
  }

  if (isShortText.value && !correctText.value.trim()) {
    errorMsg.value = t('exams.validation_short_text_required')
    return
  }

  submitting.value = true
  try {
    const altList = alternativeAnswers.value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    const fileTypes = allowedFileTypes.value
      .split(',')
      .map((s) => s.trim().replace(/^\.+/, '').toLowerCase())
      .filter(Boolean)

    const payload: QuestionPayload = {
      type: type.value,
      title: title.value.trim(),
      explanation: explanation.value.trim() || null,
      points: String(points.value),
      required: required.value,
      order_index: props.question?.order_index ?? 0,
      code_language: isCode.value ? codeLanguage.value.trim() || null : null,
      code_initial: isCode.value ? codeInitial.value || null : null,
      max_file_size_mb: isFileUpload.value ? maxFileSizeMb.value : null,
      allowed_file_types: isFileUpload.value && fileTypes.length ? fileTypes : null,
      exact_match: exactMatch.value,
      case_sensitive: caseSensitive.value,
      correct_text: isShortText.value ? correctText.value.trim() : null,
      alternative_answers: isShortText.value && altList.length ? altList : null,
      options: hasOptions.value
        ? options.value
            .filter((o) => o.text.trim())
            .map((o, i) => ({
              text: o.text.trim(),
              is_correct: o.is_correct,
              explanation: o.explanation || null,
              order_index: i,
            }))
        : [],
    }

    let result: QuestionPublic
    if (props.question) {
      result = await questionsApi.update(props.question.id, payload)
    } else {
      result = await questionsApi.create(props.examId, payload)
    }

    // Phase 9d — code question'da test case'larni saqlash
    if (isCode.value && result.id) {
      try {
        await persistTestCases(result.id)
      } catch (e) {
        errorMsg.value = extractErrorMessage(e, t('exams.test_case_save_error'))
        submitting.value = false
        return
      }
    }

    emit('saved', result)
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="
      question ? t('exams.question_drawer_edit_title') : t('exams.question_drawer_new_title')
    "
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="question-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('exams.field_question_type')" required>
        <UiSelect v-model="type" :options="typeOptions" :disabled="!!question" />
      </UiFormField>

      <UiFormField :label="t('exams.field_question_title')" required>
        <textarea
          v-model="title"
          rows="2"
          required
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('exams.field_points')" required>
          <UiInput v-model.number="points" type="number" min="0" step="0.5" required />
        </UiFormField>
        <UiFormField :label="t('exams.field_required')">
          <label class="flex items-center gap-2 text-[13px] h-9">
            <input v-model="required" type="checkbox" />
            {{ t('exams.field_required_hint') }}
          </label>
        </UiFormField>
      </div>

      <UiFormField :label="t('exams.field_explanation')">
        <textarea
          v-model="explanation"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <!-- Options (single/multiple/true_false) -->
      <div v-if="hasOptions" class="mt-4">
        <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
          {{ t('exams.section_options') }}
        </div>

        <div class="space-y-2">
          <div
            v-for="(opt, idx) in options"
            :key="idx"
            class="flex items-start gap-2"
          >
            <div class="pt-2">
              <input
                v-if="type === 'single_choice' || type === 'true_false'"
                type="radio"
                :checked="opt.is_correct"
                :disabled="type === 'true_false'"
                @change="onSingleSelect(idx)"
              />
              <input
                v-else
                v-model="opt.is_correct"
                type="checkbox"
              />
            </div>
            <input
              v-model="opt.text"
              :disabled="type === 'true_false'"
              :placeholder="t('exams.option_text_placeholder')"
              class="flex-1 rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
            />
            <UiButton
              v-if="type !== 'true_false'"
              variant="ghost"
              size="sm"
              type="button"
              :disabled="options.length <= 2"
              @click="removeOption(idx)"
            >
              ×
            </UiButton>
          </div>
        </div>

        <UiButton
          v-if="type !== 'true_false'"
          variant="ghost"
          size="sm"
          type="button"
          class="mt-2"
          @click="addOption"
        >
          + {{ t('exams.add_option') }}
        </UiButton>
      </div>

      <!-- Short text -->
      <div v-if="isShortText" class="mt-4">
        <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
          {{ t('exams.section_short_text') }}
        </div>

        <UiFormField :label="t('exams.field_correct_text')" required>
          <UiInput v-model="correctText" required />
        </UiFormField>

        <UiFormField :label="t('exams.field_alternative_answers')">
          <textarea
            v-model="alternativeAnswers"
            rows="3"
            :placeholder="t('exams.field_alternative_answers_placeholder')"
            class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
          ></textarea>
        </UiFormField>

        <div class="grid grid-cols-2 gap-3 mt-2">
          <label class="flex items-center gap-2 text-[13px]">
            <input v-model="exactMatch" type="checkbox" />
            {{ t('exams.field_exact_match') }}
          </label>
          <label class="flex items-center gap-2 text-[13px]">
            <input v-model="caseSensitive" type="checkbox" />
            {{ t('exams.field_case_sensitive') }}
          </label>
        </div>
      </div>

      <!-- Code -->
      <div v-if="isCode" class="mt-4">
        <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
          {{ t('exams.section_code') }}
        </div>

        <div class="grid grid-cols-2 gap-3">
          <UiFormField :label="t('exams.field_code_language')">
            <UiInput v-model="codeLanguage" placeholder="python, js, cpp, ..." />
          </UiFormField>
        </div>

        <UiFormField :label="t('exams.field_code_initial')">
          <textarea
            v-model="codeInitial"
            rows="6"
            class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[12px] font-mono px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
          ></textarea>
        </UiFormField>

        <!-- Phase 9d — Test cases editor -->
        <div class="mt-4">
          <div class="flex items-center justify-between mb-2">
            <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
              {{ t('exams.section_test_cases') }}
            </div>
            <UiButton type="button" variant="ghost" size="sm" @click="addTestCase">
              + {{ t('exams.add_test_case') }}
            </UiButton>
          </div>

          <div v-if="loadingTestCases" class="text-[12px] text-muted-foreground py-2">
            {{ t('common.loading') }}
          </div>

          <div
            v-else-if="codeTestCases.length === 0"
            class="text-[12px] text-muted-foreground border border-dashed border-border rounded-md p-4 text-center"
          >
            {{ t('exams.no_test_cases') }}
          </div>

          <div v-else class="space-y-2.5">
            <div
              v-for="(tc, idx) in codeTestCases"
              :key="tc.id ?? `new-${idx}`"
              class="border border-border rounded-md p-3 space-y-2"
            >
              <div class="flex items-center gap-2">
                <span class="text-[11px] font-mono text-muted-foreground">#{{ idx + 1 }}</span>
                <label class="flex items-center gap-1.5 text-[12px]">
                  <input v-model="tc.is_hidden" type="checkbox" />
                  {{ t('exams.test_case_hidden') }}
                </label>
                <input
                  v-model.number="tc.weight"
                  type="number"
                  min="0"
                  max="100"
                  step="0.5"
                  class="ml-auto w-16 text-right rounded border border-border-strong bg-background text-foreground text-[12px] px-2 py-0.5"
                  :title="t('exams.test_case_weight')"
                />
                <UiButton variant="ghost" size="sm" type="button" @click="removeTestCase(idx)">
                  ×
                </UiButton>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <div class="text-[10px] font-mono uppercase text-muted-foreground mb-1">
                    {{ t('exams.test_case_stdin') }}
                  </div>
                  <textarea
                    v-model="tc.stdin"
                    rows="3"
                    spellcheck="false"
                    placeholder="(empty)"
                    class="block w-full rounded border border-border-strong bg-muted/30 text-foreground text-[12px] font-mono px-2 py-1.5 outline-none focus:border-foreground focus:shadow-focus"
                  ></textarea>
                </div>
                <div>
                  <div class="text-[10px] font-mono uppercase text-muted-foreground mb-1">
                    {{ t('exams.test_case_expected') }}
                  </div>
                  <textarea
                    v-model="tc.expected_stdout"
                    rows="3"
                    spellcheck="false"
                    class="block w-full rounded border border-border-strong bg-muted/30 text-foreground text-[12px] font-mono px-2 py-1.5 outline-none focus:border-foreground focus:shadow-focus"
                  ></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- File upload -->
      <div v-if="isFileUpload" class="mt-4">
        <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-2">
          {{ t('exams.section_file_upload') }}
        </div>

        <div class="grid grid-cols-2 gap-3">
          <UiFormField :label="t('exams.field_max_file_size_mb')">
            <UiInput v-model.number="maxFileSizeMb" type="number" min="1" max="200" />
          </UiFormField>
          <UiFormField :label="t('exams.field_allowed_file_types')">
            <UiInput v-model="allowedFileTypes" placeholder="pdf, docx, zip" />
          </UiFormField>
        </div>
      </div>

      <UiAlert v-if="isManualOnly" variant="info" class="mt-4">
        {{ t('exams.manual_grading_notice') }}
      </UiAlert>
    </form>

    <template #footer>
      <UiButton variant="ghost" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
      <UiButton type="submit" form="question-form" :loading="submitting">
        {{ t('common.save') }}
      </UiButton>
    </template>
  </UiDrawer>
</template>
