<script setup lang="ts">
import { ref, watch } from 'vue'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { extractErrorMessage } from '@shared/api/client'
import { facultiesApi } from '@shared/api/academic'
import type { Faculty } from '@shared/types/academic'

interface Props {
  open: boolean
  faculty?: Faculty | null
}
const props = withDefaults(defineProps<Props>(), { faculty: null })
const emit = defineEmits<{ close: []; saved: [] }>()

const code = ref('')
const name = ref('')
const shortName = ref('')
const isActive = ref(true)

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

watch(
  () => [props.open, props.faculty],
  () => {
    errorMsg.value = null
    if (!props.open) return
    if (props.faculty) {
      code.value = props.faculty.code
      name.value = props.faculty.name
      shortName.value = props.faculty.short_name ?? ''
      isActive.value = props.faculty.is_active
    } else {
      code.value = ''
      name.value = ''
      shortName.value = ''
      isActive.value = true
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    // Single-tenant: organization_id avto XIU (backend service to'ldiradi)
    const payload = {
      code: code.value.trim(),
      name: name.value.trim(),
      short_name: shortName.value.trim() || null,
      dean_id: props.faculty?.dean_id ?? null,
      is_active: isActive.value,
    }
    if (props.faculty) {
      await facultiesApi.update(props.faculty.id, payload)
    } else {
      await facultiesApi.create(payload as Parameters<typeof facultiesApi.create>[0])
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
  <UiDrawer
    :open="open"
    :title="faculty ? 'Fakultet tahrir' : 'Yangi fakultet'"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="faculty-form" @submit.prevent="handleSubmit">
      <UiFormField label="Kod" required>
        <UiInput v-model="code" required />
      </UiFormField>

      <UiFormField label="To'liq nom" required>
        <UiInput v-model="name" required />
      </UiFormField>

      <UiFormField label="Qisqa nom">
        <UiInput v-model="shortName" />
      </UiFormField>

      <label class="flex items-center gap-2 mb-4 cursor-pointer">
        <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">Faol</span>
      </label>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">Bekor</UiButton>
        <UiButton type="submit" form="faculty-form" :loading="submitting">
          {{ faculty ? 'Saqlash' : 'Yaratish' }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
