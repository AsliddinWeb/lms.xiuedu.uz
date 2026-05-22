<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { examsApi } from '@shared/api/exams'
import { lessonsApi, modulesApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import type { Exam, ExamPayload, ExamType } from '@shared/types/exams'
import type { Lesson, Module } from '@shared/types/courses'

interface Props {
  open: boolean
  courseId: number
  exam?: Exam | null
}
const props = withDefaults(defineProps<Props>(), { exam: null })
const emit = defineEmits<{ close: []; saved: [exam: Exam] }>()

const { t } = useI18n()

const title = ref('')
const description = ref('')
const type = ref<ExamType>('quiz')
const lessonId = ref<number | null>(null)
const durationMinutes = ref(60)
const maxAttempts = ref(1)
const passingScore = ref(60)
const shuffleQuestions = ref(true)
const shuffleOptions = ref(true)
const showCorrectAnswers = ref(false)
const questionCount = ref<number | null>(null)

const proctoringEnabled = ref(true)
const requireFaceId = ref(true)
const requireScreenShare = ref(true)
const allowTabSwitch = ref(false)
const maxFaceLossSeconds = ref(10)

const availableFrom = ref('')
const availableUntil = ref('')

const allLessons = ref<Lesson[]>([])
const submitting = ref(false)
const errorMsg = ref<string | null>(null)

const typeOptions = computed(() => [
  { value: 'quiz', label: t('exams.type_quiz') },
  { value: 'midterm', label: t('exams.type_midterm') },
  { value: 'final', label: t('exams.type_final') },
  { value: 'dak', label: t('exams.type_dak') },
])

const lessonOptions = computed(() => [
  { value: '', label: t('exams.field_no_lesson') },
  ...allLessons.value.map((l) => ({ value: l.id, label: l.title })),
])

async function loadLessons() {
  const mods: Module[] = await modulesApi.list(props.courseId)
  const lessons: Lesson[] = []
  for (const m of mods) {
    const list = await lessonsApi.list(m.id)
    lessons.push(...list)
  }
  allLessons.value = lessons
}

function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromLocalInput(v: string): string | null {
  if (!v) return null
  return new Date(v).toISOString()
}

function reset() {
  errorMsg.value = null
  if (props.exam) {
    const e = props.exam
    title.value = e.title
    description.value = e.description ?? ''
    type.value = e.type
    lessonId.value = e.lesson_id
    durationMinutes.value = e.duration_minutes
    maxAttempts.value = e.max_attempts
    passingScore.value = Number(e.passing_score)
    shuffleQuestions.value = e.shuffle_questions
    shuffleOptions.value = e.shuffle_options
    showCorrectAnswers.value = e.show_correct_answers
    questionCount.value = e.question_count
    proctoringEnabled.value = e.proctoring_enabled
    requireFaceId.value = e.require_face_id
    requireScreenShare.value = e.require_screen_share
    allowTabSwitch.value = e.allow_tab_switch
    maxFaceLossSeconds.value = e.max_face_loss_seconds
    availableFrom.value = toLocalInput(e.available_from)
    availableUntil.value = toLocalInput(e.available_until)
  } else {
    title.value = ''
    description.value = ''
    type.value = 'quiz'
    lessonId.value = null
    durationMinutes.value = 60
    maxAttempts.value = 1
    passingScore.value = 60
    shuffleQuestions.value = true
    shuffleOptions.value = true
    showCorrectAnswers.value = false
    questionCount.value = null
    proctoringEnabled.value = true
    requireFaceId.value = true
    requireScreenShare.value = true
    allowTabSwitch.value = false
    maxFaceLossSeconds.value = 10
    availableFrom.value = ''
    availableUntil.value = ''
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      reset()
      loadLessons()
    }
  },
)

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    const payload: ExamPayload = {
      course_id: props.courseId,
      lesson_id: lessonId.value,
      title: title.value.trim(),
      description: description.value.trim() || null,
      type: type.value,
      duration_minutes: durationMinutes.value,
      max_attempts: maxAttempts.value,
      passing_score: String(passingScore.value),
      shuffle_questions: shuffleQuestions.value,
      shuffle_options: shuffleOptions.value,
      show_correct_answers: showCorrectAnswers.value,
      question_count: questionCount.value,
      proctoring_enabled: proctoringEnabled.value,
      require_face_id: requireFaceId.value,
      require_screen_share: requireScreenShare.value,
      allow_tab_switch: allowTabSwitch.value,
      max_face_loss_seconds: maxFaceLossSeconds.value,
      available_from: fromLocalInput(availableFrom.value),
      available_until: fromLocalInput(availableUntil.value),
    }

    let result: Exam
    if (props.exam) {
      const { course_id: _c, ...patch } = payload
      result = await examsApi.update(props.exam.id, patch)
    } else {
      result = await examsApi.create(payload)
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
    :title="exam ? t('exams.drawer_edit_title') : t('exams.drawer_new_title')"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="exam-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('exams.field_title')" required>
        <UiInput v-model="title" required />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('exams.field_type')" required>
          <UiSelect v-model="type" :options="typeOptions" />
        </UiFormField>
        <UiFormField :label="t('exams.field_lesson')">
          <UiSelect v-model="lessonId" :options="lessonOptions" />
        </UiFormField>
      </div>

      <UiFormField :label="t('exams.field_description')">
        <textarea
          v-model="description"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mt-6 mb-2">
        {{ t('exams.section_settings') }}
      </div>

      <div class="grid grid-cols-3 gap-3">
        <UiFormField :label="t('exams.field_duration_minutes')" required>
          <UiInput v-model.number="durationMinutes" type="number" min="1" max="600" required />
        </UiFormField>
        <UiFormField :label="t('exams.field_max_attempts')" required>
          <UiInput v-model.number="maxAttempts" type="number" min="1" max="20" required />
        </UiFormField>
        <UiFormField :label="t('exams.field_passing_score')" required>
          <UiInput
            v-model.number="passingScore"
            type="number"
            min="0"
            max="100"
            step="0.01"
            required
          />
        </UiFormField>
      </div>

      <UiFormField :label="t('exams.field_question_count_hint')">
        <UiInput
          v-model.number="questionCount"
          type="number"
          min="1"
          :placeholder="t('exams.field_question_count_placeholder')"
        />
      </UiFormField>

      <div class="space-y-2 mt-3">
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="shuffleQuestions" type="checkbox" />
          {{ t('exams.field_shuffle_questions') }}
        </label>
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="shuffleOptions" type="checkbox" />
          {{ t('exams.field_shuffle_options') }}
        </label>
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="showCorrectAnswers" type="checkbox" />
          {{ t('exams.field_show_correct_answers') }}
        </label>
      </div>

      <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mt-6 mb-2">
        {{ t('exams.section_proctoring') }}
      </div>

      <div class="space-y-2">
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="proctoringEnabled" type="checkbox" />
          {{ t('exams.field_proctoring_enabled') }}
        </label>
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="requireFaceId" type="checkbox" :disabled="!proctoringEnabled" />
          {{ t('exams.field_require_face_id') }}
        </label>
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="requireScreenShare" type="checkbox" :disabled="!proctoringEnabled" />
          {{ t('exams.field_require_screen_share') }}
        </label>
        <label class="flex items-center gap-2 text-[13px]">
          <input v-model="allowTabSwitch" type="checkbox" />
          {{ t('exams.field_allow_tab_switch') }}
        </label>
      </div>

      <UiFormField :label="t('exams.field_max_face_loss_seconds')" class="mt-2">
        <UiInput
          v-model.number="maxFaceLossSeconds"
          type="number"
          min="3"
          max="120"
          :disabled="!proctoringEnabled"
        />
      </UiFormField>

      <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground mt-6 mb-2">
        {{ t('exams.section_schedule') }}
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('exams.field_available_from')">
          <UiInput v-model="availableFrom" type="datetime-local" />
        </UiFormField>
        <UiFormField :label="t('exams.field_available_until')">
          <UiInput v-model="availableUntil" type="datetime-local" />
        </UiFormField>
      </div>
    </form>

    <template #footer>
      <UiButton variant="ghost" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
      <UiButton type="submit" form="exam-form" :loading="submitting">
        {{ t('common.save') }}
      </UiButton>
    </template>
  </UiDrawer>
</template>
