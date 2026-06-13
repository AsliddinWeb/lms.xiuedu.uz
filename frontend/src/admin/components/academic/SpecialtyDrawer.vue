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
import { departmentsApi, specialtiesApi } from '@shared/api/academic'
import type {
  Department,
  EducationForm,
  EducationLevel,
  LanguageCode,
  Specialty,
} from '@shared/types/academic'

interface Props {
  open: boolean
  specialty?: Specialty | null
}
const props = withDefaults(defineProps<Props>(), { specialty: null })
const emit = defineEmits<{ close: []; saved: [] }>()

const { t } = useI18n()

const allDepartments = ref<Department[]>([])

const departmentId = ref<number | null>(null)
const code = ref('')
const name = ref('')
const level = ref<EducationLevel>('bachelor')
const durationYears = ref(4)
const educationForm = ref<EducationForm>('distance')
const language = ref<LanguageCode>('uz-lat')
const distanceEnabled = ref(false)
const annualQuota = ref<number | null>(null)
const isActive = ref(true)

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const depOptions = computed(() =>
  allDepartments.value.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })),
)

const levelOptions = computed(() => [
  { value: 'bachelor', label: t('admin_academic.level_bachelor') },
  { value: 'master', label: t('admin_academic.level_master') },
  { value: 'phd', label: t('admin_academic.level_phd') },
])
const formOptions = computed(() => [
  { value: 'fulltime', label: t('admin_academic.form_fulltime') },
  { value: 'parttime', label: t('admin_academic.form_parttime') },
  { value: 'evening', label: t('admin_academic.form_evening') },
  { value: 'distance', label: t('admin_academic.form_distance') },
])
const langOptions = computed(() => [
  { value: 'uz-lat', label: t('admin_academic.lang_uz_lat') },
  { value: 'uz-cyr', label: t('admin_academic.lang_uz_cyr') },
  { value: 'ru', label: t('admin_academic.lang_ru') },
  { value: 'en', label: t('admin_academic.lang_en') },
])

// 559-qaror 15-band: real-time UI tekshiruvi
const quotaMax = computed(() => {
  if (level.value === 'bachelor') return 300
  if (level.value === 'master') return 30
  return null
})
const quotaError = computed(() => {
  if (annualQuota.value == null || quotaMax.value == null) return null
  if (annualQuota.value > quotaMax.value) {
    return t('admin_academic.spec_quota_error', {
      level:
        level.value === 'bachelor'
          ? t('admin_academic.level_bachelor')
          : t('admin_academic.level_master'),
      max: quotaMax.value,
    })
  }
  return null
})

watch(
  () => [props.open, props.specialty],
  async () => {
    errorMsg.value = null
    if (!props.open) return
    const deps = await departmentsApi.list({ page_size: 200 })
    allDepartments.value = deps.items

    if (props.specialty) {
      const s = props.specialty
      departmentId.value = s.department_id
      code.value = s.code
      name.value = s.name
      level.value = s.level
      durationYears.value = s.duration_years
      educationForm.value = s.education_form
      language.value = s.language
      distanceEnabled.value = s.distance_enabled
      annualQuota.value = s.annual_quota
      isActive.value = s.is_active
    } else {
      departmentId.value = allDepartments.value[0]?.id ?? null
      code.value = ''
      name.value = ''
      level.value = 'bachelor'
      durationYears.value = 4
      educationForm.value = 'distance'
      language.value = 'uz-lat'
      distanceEnabled.value = false
      annualQuota.value = null
      isActive.value = true
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  errorMsg.value = null
  if (!departmentId.value) {
    errorMsg.value = t('admin_academic.spec_no_department')
    return
  }
  if (quotaError.value) {
    errorMsg.value = quotaError.value
    return
  }
  submitting.value = true
  try {
    const payload = {
      department_id: departmentId.value,
      code: code.value.trim(),
      name: name.value.trim(),
      level: level.value,
      duration_years: durationYears.value,
      education_form: educationForm.value,
      language: language.value,
      distance_enabled: distanceEnabled.value,
      annual_quota: annualQuota.value,
      is_active: isActive.value,
    }
    if (props.specialty) {
      const { department_id: _d, code: _c, ...upd } = payload  // eslint-disable-line @typescript-eslint/no-unused-vars
      await specialtiesApi.update(props.specialty.id, upd)
    } else {
      await specialtiesApi.create(payload)
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
  <UiDrawer :open="open" :title="specialty ? t('admin_academic.spec_edit') : t('admin_academic.specialties_new')" width="lg" @close="emit('close')">
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <UiAlert v-if="distanceEnabled" variant="info" class="mb-4">
      {{ t('admin_academic.spec_decree14') }}
    </UiAlert>

    <form id="specialty-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('admin_academic.col_department')" required>
        <UiSelect v-model="departmentId" :options="depOptions" :disabled="!!specialty" />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('admin_academic.spec_dts_code')" hint="60611100" required>
          <UiInput v-model="code" required :disabled="!!specialty" />
        </UiFormField>
        <UiFormField :label="t('admin_academic.spec_level')" required>
          <UiSelect v-model="level" :options="levelOptions" />
        </UiFormField>
      </div>

      <UiFormField :label="t('admin_academic.spec_name')" required>
        <UiInput v-model="name" required />
      </UiFormField>

      <div class="grid grid-cols-3 gap-3">
        <UiFormField :label="t('admin_academic.spec_duration')" required>
          <UiInput v-model="durationYears" type="number" required />
        </UiFormField>
        <UiFormField :label="t('admin_academic.spec_form')" required>
          <UiSelect v-model="educationForm" :options="formOptions" />
        </UiFormField>
        <UiFormField :label="t('admin_academic.col_language')" required>
          <UiSelect v-model="language" :options="langOptions" />
        </UiFormField>
      </div>

      <UiFormField
        :label="quotaMax ? `${t('admin_academic.spec_quota')} — ${t('admin_academic.spec_quota_max', { n: quotaMax })}` : t('admin_academic.spec_quota')"
        :hint="quotaMax ? t('admin_academic.spec_quota_hint') : t('admin_academic.spec_quota_phd')"
        :error="quotaError"
      >
        <UiInput v-model="annualQuota" type="number" :has-error="!!quotaError" />
      </UiFormField>

      <label class="flex items-center gap-2 mb-3 cursor-pointer">
        <input v-model="distanceEnabled" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">{{ t('admin_academic.spec_distance_label') }}</span>
      </label>
      <label class="flex items-center gap-2 mb-4 cursor-pointer">
        <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">{{ t('common.active') }}</span>
      </label>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" form="specialty-form" :loading="submitting"
          :disabled="!!quotaError">
          {{ specialty ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
