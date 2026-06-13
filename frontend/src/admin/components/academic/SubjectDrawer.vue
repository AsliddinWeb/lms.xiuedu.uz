<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { extractErrorMessage } from '@shared/api/client'
import { departmentsApi, subjectsApi } from '@shared/api/academic'
import type { Department, LanguageCode, Subject } from '@shared/types/academic'

interface Props {
  open: boolean
  subject?: Subject | null
}
const props = withDefaults(defineProps<Props>(), { subject: null })
const emit = defineEmits<{ close: []; saved: [] }>()

const { t } = useI18n()

const departmentId = ref<number | null>(null)
const code = ref('')
const name = ref('')
const shortName = ref('')
const description = ref('')
const credits = ref(3)
const lectureHours = ref(0)
const practiceHours = ref(0)
const seminarHours = ref(0)
const selfStudyHours = ref(0)
const language = ref<LanguageCode>('uz-lat')
const prereqIds = ref<Set<number>>(new Set())
const isActive = ref(true)

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const allDepartments = ref<Department[]>([])
const allSubjects = ref<Subject[]>([])

const langOptions = computed(() => [
  { value: 'uz-lat', label: t('admin_academic.lang_uz_lat') },
  { value: 'uz-cyr', label: t('admin_academic.lang_uz_cyr') },
  { value: 'ru', label: t('admin_academic.lang_ru') },
  { value: 'en', label: t('admin_academic.lang_en') },
])

const depOptions = computed(() =>
  allDepartments.value.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })),
)

watch(
  () => [props.open, props.subject],
  async () => {
    errorMsg.value = null
    if (!props.open) return

    // Departments + boshqa fanlar (pre-rekvizit uchun)
    const [deps, subs] = await Promise.all([
      departmentsApi.list({ page_size: 200 }),
      subjectsApi.list({ page_size: 500 }),
    ])
    allDepartments.value = deps.items
    allSubjects.value = subs.items.filter((s) => !props.subject || s.id !== props.subject.id)

    if (props.subject) {
      const s = props.subject
      departmentId.value = s.department_id
      code.value = s.code
      name.value = s.name
      shortName.value = s.short_name ?? ''
      description.value = s.description ?? ''
      credits.value = s.credits
      lectureHours.value = s.lecture_hours
      practiceHours.value = s.practice_hours
      seminarHours.value = s.seminar_hours
      selfStudyHours.value = s.self_study_hours
      language.value = s.language
      prereqIds.value = new Set(s.prerequisite_ids)
      isActive.value = s.is_active
    } else {
      departmentId.value = allDepartments.value[0]?.id ?? null
      code.value = ''
      name.value = ''
      shortName.value = ''
      description.value = ''
      credits.value = 3
      lectureHours.value = 0
      practiceHours.value = 0
      seminarHours.value = 0
      selfStudyHours.value = 0
      language.value = 'uz-lat'
      prereqIds.value = new Set()
      isActive.value = true
    }
  },
  { immediate: true },
)

function togglePrereq(id: number) {
  const next = new Set(prereqIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  prereqIds.value = next
}

async function handleSubmit() {
  errorMsg.value = null
  if (!departmentId.value) {
    errorMsg.value = t('admin_academic.spec_no_department')
    return
  }
  submitting.value = true
  try {
    const payload = {
      department_id: departmentId.value,
      code: code.value.trim(),
      name: name.value.trim(),
      short_name: shortName.value.trim() || null,
      description: description.value.trim() || null,
      credits: credits.value,
      lecture_hours: lectureHours.value,
      practice_hours: practiceHours.value,
      seminar_hours: seminarHours.value,
      self_study_hours: selfStudyHours.value,
      language: language.value,
      prerequisite_ids: Array.from(prereqIds.value),
      is_active: isActive.value,
    }
    if (props.subject) {
      const { department_id: _d, code: _c, ...upd } = payload  // eslint-disable-line @typescript-eslint/no-unused-vars
      await subjectsApi.update(props.subject.id, upd)
    } else {
      await subjectsApi.create(payload)
    }
    emit('saved')
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer :open="open" :title="subject ? t('admin_academic.subject_edit') : t('admin_academic.subjects_new')" width="lg" @close="emit('close')">
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <form id="subject-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('admin_academic.col_department')" required>
        <UiSelect v-model="departmentId" :options="depOptions" :disabled="!!subject" />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('admin_academic.col_code')" required>
          <UiInput v-model="code" required :disabled="!!subject" placeholder="PROG-101" />
        </UiFormField>
        <UiFormField :label="t('admin_academic.subject_f_credits')" required>
          <UiInput v-model="credits" type="number" required />
        </UiFormField>
      </div>

      <UiFormField :label="t('admin_academic.subject_f_name')" required>
        <UiInput v-model="name" required />
      </UiFormField>

      <UiFormField :label="t('admin_academic.faculty_f_short')">
        <UiInput v-model="shortName" />
      </UiFormField>

      <UiFormField :label="t('admin_academic.subject_f_desc')">
        <textarea
          v-model="description"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField :label="t('admin_academic.col_language')">
        <UiSelect v-model="language" :options="langOptions" />
      </UiFormField>

      <div class="text-xs font-medium text-foreground mb-2 mt-2">{{ t('admin_academic.subject_hours') }}</div>
      <div class="grid grid-cols-4 gap-2">
        <UiFormField :label="t('admin_academic.subject_h_lecture')">
          <UiInput v-model="lectureHours" type="number" />
        </UiFormField>
        <UiFormField :label="t('admin_academic.subject_h_practice')">
          <UiInput v-model="practiceHours" type="number" />
        </UiFormField>
        <UiFormField :label="t('admin_academic.subject_h_seminar')">
          <UiInput v-model="seminarHours" type="number" />
        </UiFormField>
        <UiFormField :label="t('admin_academic.subject_h_self')">
          <UiInput v-model="selfStudyHours" type="number" />
        </UiFormField>
      </div>

      <div class="mt-2 mb-4">
        <div class="text-xs font-medium text-foreground mb-2">
          {{ t('admin_academic.subject_prereq_n', { n: prereqIds.size }) }}
        </div>
        <div class="border border-border rounded-md p-2 max-h-48 overflow-y-auto">
          <label
            v-for="s in allSubjects"
            :key="s.id"
            class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-muted cursor-pointer"
          >
            <input
              type="checkbox"
              :checked="prereqIds.has(s.id)"
              @change="togglePrereq(s.id)"
              class="w-3.5 h-3.5 accent-foreground"
            />
            <span class="font-mono text-[12px]">{{ s.code }}</span>
            <span class="text-[13px] text-muted-foreground">{{ s.name }}</span>
          </label>
          <div v-if="allSubjects.length === 0" class="text-[12px] text-muted-foreground p-2 italic">
            {{ t('admin_academic.subject_no_other') }}
          </div>
        </div>
      </div>

      <label class="flex items-center gap-2 mb-4 cursor-pointer">
        <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">{{ t('common.active') }}</span>
      </label>
    </form>
    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" form="subject-form" :loading="submitting">
          {{ subject ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
