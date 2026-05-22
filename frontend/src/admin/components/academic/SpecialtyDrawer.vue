<script setup lang="ts">
import { computed, ref, watch } from 'vue'

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

const levelOptions = [
  { value: 'bachelor', label: 'Bakalavr' },
  { value: 'master', label: 'Magistr' },
  { value: 'phd', label: 'PhD' },
]
const formOptions = [
  { value: 'fulltime', label: 'Kunduzgi' },
  { value: 'parttime', label: 'Sirtqi' },
  { value: 'evening', label: 'Kechki' },
  { value: 'distance', label: 'Masofaviy' },
]
const langOptions = [
  { value: 'uz-lat', label: "O'zbek (lotin)" },
  { value: 'uz-cyr', label: "O'zbek (kirill)" },
  { value: 'ru', label: 'Rus' },
  { value: 'en', label: 'Ingliz' },
]

// 559-qaror 15-band: real-time UI tekshiruvi
const quotaMax = computed(() => {
  if (level.value === 'bachelor') return 300
  if (level.value === 'master') return 30
  return null
})
const quotaError = computed(() => {
  if (annualQuota.value == null || quotaMax.value == null) return null
  if (annualQuota.value > quotaMax.value) {
    return `${level.value === 'bachelor' ? 'Bakalavr' : 'Magistr'} uchun max ${
      quotaMax.value
    } (559-qaror 15-band)`
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
    errorMsg.value = 'Kafedra tanlanmagan'
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
    errorMsg.value = extractErrorMessage(e, 'Saqlashda xato')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer :open="open" :title="specialty ? 'Yo\'nalish tahrir' : 'Yangi yo\'nalish'" width="lg" @close="emit('close')">
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <UiAlert v-if="distanceEnabled" variant="info" class="mb-4">
      <strong>559-qaror 14-band:</strong> Masofaviy ta'limga ruxsat berilgan yo'nalish.
      Talabalar onlayn o'qishi mumkin.
    </UiAlert>

    <form id="specialty-form" @submit.prevent="handleSubmit">
      <UiFormField label="Kafedra" required>
        <UiSelect v-model="departmentId" :options="depOptions" :disabled="!!specialty" />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField label="DTS kodi" hint="60611100" required>
          <UiInput v-model="code" required :disabled="!!specialty" />
        </UiFormField>
        <UiFormField label="Daraja" required>
          <UiSelect v-model="level" :options="levelOptions" />
        </UiFormField>
      </div>

      <UiFormField label="Yo'nalish nomi" required>
        <UiInput v-model="name" required />
      </UiFormField>

      <div class="grid grid-cols-3 gap-3">
        <UiFormField label="Davomiyligi (yil)" required>
          <UiInput v-model="durationYears" type="number" required />
        </UiFormField>
        <UiFormField label="Ta'lim shakli" required>
          <UiSelect v-model="educationForm" :options="formOptions" />
        </UiFormField>
        <UiFormField label="Til" required>
          <UiSelect v-model="language" :options="langOptions" />
        </UiFormField>
      </div>

      <UiFormField
        :label="`Yillik qabul rejasi (annual quota)${quotaMax ? ` — max ${quotaMax}` : ''}`"
        :hint="
          quotaMax
            ? `559-qaror 15-band: bakalavr 300, magistr 30, PhD chegarasiz`
            : 'PhD uchun chegarasiz'
        "
        :error="quotaError"
      >
        <UiInput v-model="annualQuota" type="number" :has-error="!!quotaError" />
      </UiFormField>

      <label class="flex items-center gap-2 mb-3 cursor-pointer">
        <input v-model="distanceEnabled" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">Masofaviy ta'limga ruxsat (559-qaror 14-band)</span>
      </label>
      <label class="flex items-center gap-2 mb-4 cursor-pointer">
        <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">Faol</span>
      </label>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">Bekor</UiButton>
        <UiButton type="submit" form="specialty-form" :loading="submitting"
          :disabled="!!quotaError">
          {{ specialty ? 'Saqlash' : 'Yaratish' }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
