<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { assignmentsApi, rubricsApi } from '@shared/api/assignments'
import { lessonsApi, modulesApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import type {
  Assignment,
  AssignmentPayload,
  AssignmentType,
  Rubric,
} from '@shared/types/assignments'
import type { Lesson, Module } from '@shared/types/courses'

interface Props {
  open: boolean
  courseId: number
  assignment?: Assignment | null
}
const props = withDefaults(defineProps<Props>(), { assignment: null })
const emit = defineEmits<{ close: []; saved: [assignment: Assignment] }>()

const { t } = useI18n()

const title = ref('')
const description = ref('')
const instructions = ref('')
const type = ref<AssignmentType>('essay')
const lessonId = ref<number | null>(null)
const dueDate = ref('')
const availableFrom = ref('')
const closedAt = ref('')
const maxScore = ref<number>(100)
const passScore = ref<number | ''>('')
const maxAttempts = ref<number>(1)
const lateAllowed = ref(true)
const latePenalty = ref<number>(0)
const allowedTypesText = ref('')
const maxFileSize = ref<number>(50)
const rubricId = ref<number | null>(null)
const isPublished = ref(false)

const modules = ref<Module[]>([])
const lessons = ref<Lesson[]>([])
const rubrics = ref<Rubric[]>([])

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const typeOptions = computed(() => [
  { value: 'essay', label: t('assignments.type_essay') },
  { value: 'file', label: t('assignments.type_file') },
])

const lessonOptions = computed(() => {
  const out: Array<{ value: number | null; label: string }> = [
    { value: null, label: t('teacher_assignments.field_lesson_none') },
  ]
  for (const m of modules.value) {
    const ls = lessons.value.filter((l) => l.module_id === m.id)
    for (const l of ls) {
      out.push({ value: l.id, label: `${m.title} → ${l.title}` })
    }
  }
  return out
})

const rubricOptions = computed(() => [
  { value: null as number | null, label: t('teacher_assignments.field_rubric_none') },
  ...rubrics.value.map((r) => ({
    value: r.id,
    label: `${r.title} (${r.total_points})`,
  })),
])

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  // datetime-local input "YYYY-MM-DDTHH:MM" expects local time
  const tzOffsetMs = d.getTimezoneOffset() * 60000
  const localIso = new Date(d.getTime() - tzOffsetMs).toISOString().slice(0, 16)
  return localIso
}

function fromLocalInput(local: string): string | null {
  if (!local) return null
  // local "YYYY-MM-DDTHH:MM" → ISO with timezone
  return new Date(local).toISOString()
}

watch(
  () => [props.open, props.assignment],
  async () => {
    errorMsg.value = null
    if (!props.open) return

    // Modullar/darslar (lesson picker uchun)
    try {
      const ms = await modulesApi.list(props.courseId)
      modules.value = ms
      const all: Lesson[] = []
      await Promise.all(
        ms.map(async (m) => {
          const ls = await lessonsApi.list(m.id)
          all.push(...ls)
        }),
      )
      lessons.value = all
    } catch {
      modules.value = []
      lessons.value = []
    }

    // Rubrik kataloglari
    try {
      const data = await rubricsApi.list({ page_size: 100 })
      rubrics.value = data.items
    } catch {
      rubrics.value = []
    }

    const a = props.assignment
    if (a) {
      title.value = a.title
      description.value = a.description ?? ''
      instructions.value = a.instructions ?? ''
      type.value = a.type
      lessonId.value = a.lesson_id
      dueDate.value = toLocalInput(a.due_date)
      availableFrom.value = toLocalInput(a.available_from)
      closedAt.value = toLocalInput(a.closed_at)
      maxScore.value = Number(a.max_score)
      passScore.value = a.pass_score === null ? '' : Number(a.pass_score)
      maxAttempts.value = a.max_attempts
      lateAllowed.value = a.late_submission_allowed
      latePenalty.value = Number(a.late_penalty_per_day)
      allowedTypesText.value = a.allowed_file_types.join(', ')
      maxFileSize.value = a.max_file_size_mb
      rubricId.value = a.rubric_id
      isPublished.value = a.is_published
    } else {
      title.value = ''
      description.value = ''
      instructions.value = ''
      type.value = 'essay'
      lessonId.value = null
      // Default due: tomorrow 23:59
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      tomorrow.setHours(23, 59, 0, 0)
      dueDate.value = toLocalInput(tomorrow.toISOString())
      availableFrom.value = ''
      closedAt.value = ''
      maxScore.value = 100
      passScore.value = ''
      maxAttempts.value = 1
      lateAllowed.value = true
      latePenalty.value = 0
      allowedTypesText.value = ''
      maxFileSize.value = 50
      rubricId.value = null
      isPublished.value = false
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    const allowed = allowedTypesText.value
      .split(',')
      .map((t) => t.trim().toLowerCase().replace(/^\.+/, ''))
      .filter(Boolean)

    const payload: AssignmentPayload = {
      course_id: props.courseId,
      lesson_id: lessonId.value,
      title: title.value.trim(),
      description: description.value.trim() || null,
      instructions: instructions.value.trim() || null,
      type: type.value,
      due_date: fromLocalInput(dueDate.value)!,
      available_from: fromLocalInput(availableFrom.value),
      closed_at: fromLocalInput(closedAt.value),
      max_score: String(maxScore.value),
      pass_score: passScore.value === '' ? null : String(passScore.value),
      max_attempts: maxAttempts.value,
      late_submission_allowed: lateAllowed.value,
      late_penalty_per_day: String(latePenalty.value),
      allowed_file_types: allowed,
      max_file_size_mb: maxFileSize.value,
      rubric_id: rubricId.value,
    }

    let result: Assignment
    if (props.assignment) {
      const { course_id: _c, ...patch } = payload
      result = await assignmentsApi.update(props.assignment.id, patch)
    } else {
      result = await assignmentsApi.create(payload)
    }

    if (isPublished.value !== result.is_published) {
      result = await assignmentsApi.setPublished(result.id, isPublished.value)
    }

    emit('saved', result)
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, 'Saqlashda xato')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="
      assignment
        ? t('teacher_assignments.drawer_edit_title')
        : t('teacher_assignments.drawer_new_title')
    "
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="assignment-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('teacher_assignments.field_title')" required>
        <UiInput v-model="title" required />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('teacher_assignments.field_type')" required>
          <UiSelect v-model="type" :options="typeOptions" />
        </UiFormField>
        <UiFormField :label="t('teacher_assignments.field_lesson')">
          <UiSelect v-model="lessonId" :options="lessonOptions" />
        </UiFormField>
      </div>

      <UiFormField :label="t('teacher_assignments.field_description')">
        <textarea
          v-model="description"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField :label="t('teacher_assignments.field_instructions')">
        <textarea
          v-model="instructions"
          rows="3"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <div class="grid grid-cols-3 gap-3">
        <UiFormField :label="t('teacher_assignments.field_available_from')">
          <input
            v-model="availableFrom"
            type="datetime-local"
            class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
          />
        </UiFormField>
        <UiFormField :label="t('teacher_assignments.field_due_date')" required>
          <input
            v-model="dueDate"
            type="datetime-local"
            required
            class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
          />
        </UiFormField>
        <UiFormField :label="t('teacher_assignments.field_closed_at')">
          <input
            v-model="closedAt"
            type="datetime-local"
            class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
          />
        </UiFormField>
      </div>

      <div class="grid grid-cols-3 gap-3">
        <UiFormField :label="t('teacher_assignments.field_max_score')">
          <UiInput v-model="maxScore" type="number" min="0" max="999" />
        </UiFormField>
        <UiFormField :label="t('teacher_assignments.field_pass_score')">
          <UiInput v-model="passScore" type="number" min="0" max="999" />
        </UiFormField>
        <UiFormField :label="t('teacher_assignments.field_max_attempts')">
          <UiInput v-model="maxAttempts" type="number" min="1" max="20" />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('teacher_assignments.field_late_penalty')">
          <UiInput v-model="latePenalty" type="number" min="0" max="100" step="0.5" />
        </UiFormField>
        <label
          class="flex items-center gap-2 cursor-pointer mt-7 text-[13px]"
        >
          <input
            v-model="lateAllowed"
            type="checkbox"
            class="w-3.5 h-3.5 accent-foreground"
          />
          <span>{{ t('teacher_assignments.field_late_allowed') }}</span>
        </label>
      </div>

      <template v-if="type === 'file'">
        <div class="grid grid-cols-2 gap-3">
          <UiFormField :label="t('teacher_assignments.field_allowed_types')">
            <UiInput v-model="allowedTypesText" placeholder="pdf, docx, zip" />
            <div class="text-[11px] text-muted-foreground mt-1">
              {{ t('teacher_assignments.field_allowed_types_hint') }}
            </div>
          </UiFormField>
          <UiFormField :label="t('teacher_assignments.field_max_file_size')">
            <UiInput v-model="maxFileSize" type="number" min="1" max="200" />
          </UiFormField>
        </div>
      </template>

      <UiFormField :label="t('teacher_assignments.field_rubric')">
        <UiSelect v-model="rubricId" :options="rubricOptions" />
      </UiFormField>

      <label class="flex items-center gap-2 mt-2 cursor-pointer text-[13px]">
        <input
          v-model="isPublished"
          type="checkbox"
          class="w-3.5 h-3.5 accent-foreground"
        />
        <span>{{ t('teacher_assignments.is_published_label') }}</span>
      </label>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="assignment-form" :loading="submitting">
          {{ assignment ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
