<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { appealsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { Appeal, AppealRespondPayload } from '@shared/types/assignments'

interface Props {
  open: boolean
  appeal: Appeal | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ close: []; responded: [appeal: Appeal] }>()

const { t } = useI18n()

type Decision = 'approved' | 'rejected'
const decision = ref<Decision>('approved')
const newScore = ref<number | ''>('')
const response = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

const decisionOptions = [
  { value: 'approved' as Decision, label: t('appeals.decision_approve') },
  { value: 'rejected' as Decision, label: t('appeals.decision_reject') },
]

watch(
  () => props.open,
  (v) => {
    if (v) {
      decision.value = 'approved'
      newScore.value = ''
      response.value = ''
      error.value = null
    }
  },
)

async function handleSubmit() {
  if (!props.appeal) return
  error.value = null
  if (decision.value === 'approved' && newScore.value === '') {
    error.value = t('appeals.new_score_required')
    return
  }
  submitting.value = true
  try {
    const payload: AppealRespondPayload = {
      status: decision.value,
      response: response.value.trim() || null,
    }
    if (decision.value === 'approved') {
      payload.new_score = Number(newScore.value)
    }
    const updated = await appealsApi.respond(props.appeal.id, payload)
    emit('responded', updated)
    emit('close')
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="t('appeals.respond_drawer_title')"
    width="md"
    @close="emit('close')"
  >
    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <div v-if="appeal" class="mb-4 p-3 border border-border rounded-md bg-muted/30">
      <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-1">
        {{ t('appeals.reason_label') }}
      </div>
      <p class="text-[13px] leading-6 whitespace-pre-wrap">{{ appeal.reason }}</p>
    </div>

    <form id="respond-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('appeals.decision_label')" required>
        <UiSelect v-model="decision" :options="decisionOptions" />
      </UiFormField>

      <UiFormField
        v-if="decision === 'approved'"
        :label="t('appeals.new_score_label')"
        required
      >
        <UiInput v-model="newScore" type="number" min="0" max="999" step="0.5" required />
      </UiFormField>

      <UiFormField :label="t('appeals.response_label')">
        <textarea
          v-model="response"
          rows="4"
          :placeholder="t('appeals.response_placeholder')"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="respond-form" :loading="submitting">
          {{ t('appeals.respond_submit') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
