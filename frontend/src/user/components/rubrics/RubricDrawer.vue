<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { rubricsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { Rubric } from '@shared/types/assignments'

interface Props {
  open: boolean
  rubric?: Rubric | null
}
const props = withDefaults(defineProps<Props>(), { rubric: null })
const emit = defineEmits<{ close: []; saved: [rubric: Rubric] }>()

const { t } = useI18n()

interface CriterionRow {
  key: string
  name: string
  max_points: number
}

const title = ref('')
const description = ref('')
const criteria = ref<CriterionRow[]>([])

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const total = computed(() =>
  criteria.value.reduce((acc, c) => acc + (Number(c.max_points) || 0), 0),
)

const KEY_REGEX = /^[a-z][a-z0-9_]*$/

watch(
  () => [props.open, props.rubric],
  () => {
    errorMsg.value = null
    if (!props.open) return
    const r = props.rubric
    if (r) {
      title.value = r.title
      description.value = r.description ?? ''
      criteria.value = r.criteria.map((c) => ({
        key: c.key,
        name: c.name,
        max_points: Number(c.max_points),
      }))
    } else {
      title.value = ''
      description.value = ''
      criteria.value = [
        { key: 'structure', name: 'Tuzilish', max_points: 30 },
        { key: 'content', name: 'Mazmun', max_points: 70 },
      ]
    }
  },
  { immediate: true },
)

function addRow() {
  criteria.value = [
    ...criteria.value,
    { key: `criterion_${criteria.value.length + 1}`, name: '', max_points: 10 },
  ]
}

function removeRow(idx: number) {
  criteria.value = criteria.value.filter((_, i) => i !== idx)
}

async function handleSubmit() {
  errorMsg.value = null
  // Frontend validation
  if (criteria.value.length === 0) {
    errorMsg.value = 'Kamida bitta kriteriya kerak'
    return
  }
  const keys = criteria.value.map((c) => c.key.trim().toLowerCase())
  if (new Set(keys).size !== keys.length) {
    errorMsg.value = 'Kalitlar yagona bo\'lishi kerak'
    return
  }
  for (const c of criteria.value) {
    if (!KEY_REGEX.test(c.key)) {
      errorMsg.value = `Noto'g'ri kalit: '${c.key}' (${t('rubrics.field_key_hint')})`
      return
    }
    if (!c.name.trim()) {
      errorMsg.value = `'${c.key}' kriteriyasi nomi bo'sh`
      return
    }
    if (Number(c.max_points) <= 0) {
      errorMsg.value = `'${c.key}' max ball 0 dan katta bo'lishi kerak`
      return
    }
  }

  submitting.value = true
  try {
    const payload = {
      title: title.value.trim(),
      description: description.value.trim() || null,
      criteria: criteria.value.map((c) => ({
        key: c.key.trim().toLowerCase(),
        name: c.name.trim(),
        max_points: Number(c.max_points),
        levels: [],
      })),
    }
    let result: Rubric
    if (props.rubric) {
      result = await rubricsApi.update(props.rubric.id, payload as Partial<Rubric>)
    } else {
      result = await rubricsApi.create(payload)
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
    :title="rubric ? t('rubrics.drawer_edit_title') : t('rubrics.drawer_new_title')"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="rubric-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('rubrics.field_title')" required>
        <UiInput v-model="title" required />
      </UiFormField>

      <UiFormField :label="t('rubrics.field_description')">
        <textarea
          v-model="description"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <div class="mt-2">
        <div class="flex items-center justify-between mb-2">
          <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {{ t('rubrics.criteria_section') }}
          </div>
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ t('rubrics.total_label', { n: total }) }}
          </span>
        </div>

        <div class="space-y-2 mb-3">
          <div
            v-for="(c, i) in criteria"
            :key="i"
            class="grid grid-cols-[1fr_2fr_90px_auto] gap-2 items-start"
          >
            <UiFormField :label="i === 0 ? t('rubrics.field_key') : ''">
              <UiInput v-model="c.key" placeholder="key" />
            </UiFormField>
            <UiFormField :label="i === 0 ? t('rubrics.field_name') : ''">
              <UiInput v-model="c.name" />
            </UiFormField>
            <UiFormField :label="i === 0 ? t('rubrics.field_max') : ''">
              <UiInput v-model="c.max_points" type="number" min="0" />
            </UiFormField>
            <div :class="i === 0 ? 'pt-7' : ''">
              <UiButton
                type="button"
                variant="ghost"
                size="sm"
                class="text-danger-600"
                @click="removeRow(i)"
              >
                ×
              </UiButton>
            </div>
          </div>
        </div>

        <div class="text-[11px] text-muted-foreground mb-2">
          {{ t('rubrics.field_key_hint') }}
        </div>

        <UiButton type="button" variant="outline" size="sm" @click="addRow">
          + {{ t('rubrics.add_criterion') }}
        </UiButton>
      </div>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="rubric-form" :loading="submitting">
          {{ rubric ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
