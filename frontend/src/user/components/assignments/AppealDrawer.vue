<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import { submissionsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { Appeal } from '@shared/types/assignments'

interface Props {
  open: boolean
  submissionId: number
}
const props = defineProps<Props>()
const emit = defineEmits<{ close: []; created: [appeal: Appeal] }>()

const { t } = useI18n()

const reason = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

watch(
  () => props.open,
  (v) => {
    if (v) {
      reason.value = ''
      error.value = null
    }
  },
)

async function handleSubmit() {
  error.value = null
  if (reason.value.trim().length < 10) {
    error.value = t('appeals.reason_placeholder')
    return
  }
  submitting.value = true
  try {
    const ap = await submissionsApi.createAppeal(props.submissionId, {
      reason: reason.value.trim(),
    })
    emit('created', ap)
    emit('close')
  } catch (e) {
    error.value = extractErrorMessage(e, 'Yuborishda xato')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="t('appeals.drawer_title')"
    width="md"
    @close="emit('close')"
  >
    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <form id="appeal-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('appeals.reason_label')" required>
        <textarea
          v-model="reason"
          rows="6"
          :placeholder="t('appeals.reason_placeholder')"
          required
          minlength="10"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
        <div class="text-[11px] text-muted-foreground mt-1 font-mono">
          {{ reason.length }} chars (min 10)
        </div>
      </UiFormField>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="appeal-form" :loading="submitting">
          {{ t('appeals.submit') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
