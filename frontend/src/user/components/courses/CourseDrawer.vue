<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { coursesApi } from '@shared/api/courses'
import { subjectsApi } from '@shared/api/academic'
import { extractErrorMessage } from '@shared/api/client'
import type {
  Course,
  CourseLevel,
  CoursePayload,
  CourseType,
  EnrollmentType,
  LangCode,
} from '@shared/types/courses'
import type { Subject } from '@shared/types/academic'

interface Props {
  open: boolean
  course?: Course | null
}
const props = withDefaults(defineProps<Props>(), { course: null })
const emit = defineEmits<{ close: []; saved: [course: Course] }>()

const { t } = useI18n()

const title = ref('')
const slug = ref('')
const code = ref('')
const description = ref('')
const subjectId = ref<number | null>(null)
const type = ref<CourseType>('open')
const level = ref<CourseLevel | ''>('')
const language = ref<LangCode>('uz-lat')
const durationWeeks = ref<number | ''>('')
const estimatedHours = ref<number | ''>('')
const enrollmentType = ref<EnrollmentType>('manual')
const maxStudents = ref<number | ''>('')
const objectivesText = ref('')
const skillsText = ref('')

const errorMsg = ref<string | null>(null)
const submitting = ref(false)
const subjects = ref<Subject[]>([])

const typeOptions = computed(() => [
  { value: 'academic', label: t('courses.type_academic') },
  { value: 'open', label: t('courses.type_open') },
  { value: 'micro', label: t('courses.type_micro') },
  { value: 'specialization', label: t('courses.type_specialization') },
])

const levelOptions = computed(() => [
  { value: '', label: '—' },
  { value: 'beginner', label: t('courses.level_beginner') },
  { value: 'intermediate', label: t('courses.level_intermediate') },
  { value: 'advanced', label: t('courses.level_advanced') },
])

const enrollmentOptions = computed(() => [
  { value: 'manual', label: t('courses.enrollment_manual') },
  { value: 'self', label: t('courses.enrollment_self') },
  { value: 'auto', label: t('courses.enrollment_auto') },
])

const langOptions = [
  { value: 'uz-lat', label: "O'zbek (lotin)" },
  { value: 'uz-cyr', label: "Ўзбек (kirill)" },
  { value: 'ru', label: 'Русский' },
  { value: 'en', label: 'English' },
]

const subjectOptions = computed(() => [
  { value: null as number | null, label: t('courses.field_subject_none') },
  ...subjects.value.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` })),
])

watch(
  () => [props.open, props.course],
  async () => {
    errorMsg.value = null
    if (!props.open) return
    if (subjects.value.length === 0) {
      try {
        const data = await subjectsApi.list({ page_size: 500, is_active: true })
        subjects.value = data.items
      } catch {
        // fanlar yuklanmasa ham forma ishlay beradi
      }
    }
    const c = props.course
    if (c) {
      title.value = c.title
      slug.value = c.slug
      code.value = c.code ?? ''
      description.value = c.description ?? ''
      subjectId.value = c.subject_id
      type.value = c.type
      level.value = c.level ?? ''
      language.value = c.language
      durationWeeks.value = c.duration_weeks ?? ''
      estimatedHours.value = c.estimated_hours ?? ''
      enrollmentType.value = c.enrollment_type
      maxStudents.value = c.max_students ?? ''
      objectivesText.value = c.objectives.join('\n')
      skillsText.value = c.skills_gained.join('\n')
    } else {
      title.value = ''
      slug.value = ''
      code.value = ''
      description.value = ''
      subjectId.value = null
      type.value = 'open'
      level.value = ''
      language.value = 'uz-lat'
      durationWeeks.value = ''
      estimatedHours.value = ''
      enrollmentType.value = 'manual'
      maxStudents.value = ''
      objectivesText.value = ''
      skillsText.value = ''
    }
  },
  { immediate: true },
)

function autoSlug() {
  if (props.course || slug.value) return
  const s = title.value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 60)
  slug.value = s
}

function splitLines(s: string): string[] {
  return s
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
}

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    const payload: CoursePayload = {
      title: title.value.trim(),
      slug: slug.value.trim(),
      code: code.value.trim() || null,
      description: description.value.trim() || null,
      subject_id: subjectId.value,
      type: type.value,
      level: level.value || null,
      language: language.value,
      duration_weeks: durationWeeks.value === '' ? null : Number(durationWeeks.value),
      estimated_hours: estimatedHours.value === '' ? null : Number(estimatedHours.value),
      enrollment_type: enrollmentType.value,
      max_students: maxStudents.value === '' ? null : Number(maxStudents.value),
      objectives: splitLines(objectivesText.value),
      skills_gained: splitLines(skillsText.value),
    }
    let result: Course
    if (props.course) {
      const { slug: _slug, ...rest } = payload
      result = await coursesApi.update(props.course.id, rest)
    } else {
      result = await coursesApi.create(payload)
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
    :title="course ? t('courses.drawer_edit_title') : t('courses.drawer_new_title')"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <form id="course-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('courses.field_title')" required>
        <UiInput v-model="title" required @blur="autoSlug" />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('courses.field_slug')" required>
          <UiInput v-model="slug" required :disabled="!!course" placeholder="my-course-2026" />
          <div class="text-[11px] text-muted-foreground mt-1">{{ t('courses.field_slug_hint') }}</div>
        </UiFormField>
        <UiFormField :label="t('courses.field_code')">
          <UiInput v-model="code" placeholder="CS-101" />
        </UiFormField>
      </div>

      <UiFormField :label="t('courses.field_description')">
        <textarea
          v-model="description"
          rows="3"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField :label="t('courses.field_subject')">
        <UiSelect v-model="subjectId" :options="subjectOptions" />
      </UiFormField>

      <div class="grid grid-cols-3 gap-3">
        <UiFormField :label="t('courses.field_type')">
          <UiSelect v-model="type" :options="typeOptions" />
        </UiFormField>
        <UiFormField :label="t('courses.field_level')">
          <UiSelect v-model="level" :options="levelOptions" />
        </UiFormField>
        <UiFormField :label="t('courses.field_language')">
          <UiSelect v-model="language" :options="langOptions" />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('courses.field_duration_weeks')">
          <UiInput v-model="durationWeeks" type="number" min="1" max="104" />
        </UiFormField>
        <UiFormField :label="t('courses.field_estimated_hours')">
          <UiInput v-model="estimatedHours" type="number" min="1" max="10000" />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('courses.field_enrollment_type')">
          <UiSelect v-model="enrollmentType" :options="enrollmentOptions" />
        </UiFormField>
        <UiFormField :label="t('courses.field_max_students')">
          <UiInput v-model="maxStudents" type="number" min="1" />
        </UiFormField>
      </div>

      <UiFormField :label="t('courses.field_objectives')">
        <textarea
          v-model="objectivesText"
          rows="3"
          placeholder="Har bir maqsad - alohida qatorda"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField :label="t('courses.field_skills')">
        <textarea
          v-model="skillsText"
          rows="3"
          placeholder="Har bir ko'nikma - alohida qatorda"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="course-form" :loading="submitting">
          {{ course ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
