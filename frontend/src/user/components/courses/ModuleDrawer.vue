<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { modulesApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import type { Module } from '@shared/types/courses'

interface Props {
  open: boolean
  courseId: number
  module?: Module | null
}
const props = withDefaults(defineProps<Props>(), { module: null })
const emit = defineEmits<{ close: []; saved: [module: Module] }>()

const { t } = useI18n()

const title = ref('')
const description = ref('')

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

watch(
  () => [props.open, props.module],
  () => {
    errorMsg.value = null
    if (!props.open) return
    if (props.module) {
      title.value = props.module.title
      description.value = props.module.description ?? ''
    } else {
      title.value = ''
      description.value = ''
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    const payload = {
      title: title.value.trim(),
      description: description.value.trim() || null,
    }
    let result: Module
    if (props.module) {
      result = await modulesApi.update(props.module.id, payload)
    } else {
      result = await modulesApi.create(props.courseId, payload)
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
    :title="module ? t('builder.module_drawer_edit') : t('builder.module_drawer_new')"
    width="md"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <form id="module-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('builder.field_module_title')" required>
        <UiInput v-model="title" required />
      </UiFormField>
      <UiFormField :label="t('builder.field_description')">
        <textarea
          v-model="description"
          rows="3"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="module-form" :loading="submitting">
          {{ module ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
