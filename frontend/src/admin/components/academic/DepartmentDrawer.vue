<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { extractErrorMessage } from '@shared/api/client'
import { departmentsApi } from '@shared/api/academic'
import type { Department } from '@shared/types/academic'

import { useAcademicStore } from '@admin/stores/academic'

interface Props {
  open: boolean
  department?: Department | null
}
const props = withDefaults(defineProps<Props>(), { department: null })
const emit = defineEmits<{ close: []; saved: [] }>()

const store = useAcademicStore()

const facultyId = ref<number | null>(null)
const code = ref('')
const name = ref('')
const isActive = ref(true)
const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const facOptions = computed(() =>
  store.faculties.map((f) => ({ value: f.id, label: `${f.code} — ${f.name}` })),
)

watch(
  () => [props.open, props.department],
  async () => {
    errorMsg.value = null
    if (!props.open) return
    await store.fetchFaculties()
    if (props.department) {
      facultyId.value = props.department.faculty_id
      code.value = props.department.code
      name.value = props.department.name
      isActive.value = props.department.is_active
    } else {
      facultyId.value = store.faculties[0]?.id ?? null
      code.value = ''
      name.value = ''
      isActive.value = true
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  errorMsg.value = null
  if (!facultyId.value) {
    errorMsg.value = 'Fakultet tanlanmagan'
    return
  }
  submitting.value = true
  try {
    const payload = {
      faculty_id: facultyId.value,
      code: code.value.trim(),
      name: name.value.trim(),
      head_id: props.department?.head_id ?? null,
      is_active: isActive.value,
    }
    if (props.department) {
      const { faculty_id: _f, ...upd } = payload  // eslint-disable-line @typescript-eslint/no-unused-vars
      await departmentsApi.update(props.department.id, upd)
    } else {
      await departmentsApi.create(payload)
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
  <UiDrawer :open="open" :title="department ? 'Kafedra tahrir' : 'Yangi kafedra'" @close="emit('close')">
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <form id="dept-form" @submit.prevent="handleSubmit">
      <UiFormField label="Fakultet" required>
        <UiSelect v-model="facultyId" :options="facOptions" :disabled="!!department" />
      </UiFormField>
      <UiFormField label="Kod" required>
        <UiInput v-model="code" required />
      </UiFormField>
      <UiFormField label="Nom" required>
        <UiInput v-model="name" required />
      </UiFormField>
      <label class="flex items-center gap-2 mb-4 cursor-pointer">
        <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">Faol</span>
      </label>
    </form>
    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">Bekor</UiButton>
        <UiButton type="submit" form="dept-form" :loading="submitting">
          {{ department ? 'Saqlash' : 'Yaratish' }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
