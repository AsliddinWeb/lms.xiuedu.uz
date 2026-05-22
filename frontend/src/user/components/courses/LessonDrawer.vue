<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { lessonsApi } from '@shared/api/courses'
import { contentApi } from '@shared/api/content'
import { extractErrorMessage } from '@shared/api/client'
import type { Lesson } from '@shared/types/courses'
import type { ContentItem } from '@shared/types/content'

import ContentPickerDrawer from '@user/components/courses/ContentPickerDrawer.vue'

interface Props {
  open: boolean
  moduleId: number
  lesson?: Lesson | null
}
const props = withDefaults(defineProps<Props>(), { lesson: null })
const emit = defineEmits<{ close: []; saved: [lesson: Lesson] }>()

const { t } = useI18n()

const title = ref('')
const description = ref('')
const estimatedMinutes = ref<number | ''>('')
const required = ref(true)
const contentId = ref<number | null>(null)
const attachedContent = ref<ContentItem | null>(null)

const errorMsg = ref<string | null>(null)
const submitting = ref(false)
const pickerOpen = ref(false)

async function loadContentSummary(id: number | null) {
  if (id === null) {
    attachedContent.value = null
    return
  }
  try {
    attachedContent.value = await contentApi.get(id)
  } catch {
    attachedContent.value = null
  }
}

watch(
  () => [props.open, props.lesson],
  async () => {
    errorMsg.value = null
    if (!props.open) return
    if (props.lesson) {
      title.value = props.lesson.title
      description.value = props.lesson.description ?? ''
      estimatedMinutes.value = props.lesson.estimated_minutes ?? ''
      required.value = props.lesson.is_required_for_completion
      contentId.value = props.lesson.primary_content_id
    } else {
      title.value = ''
      description.value = ''
      estimatedMinutes.value = ''
      required.value = true
      contentId.value = null
    }
    await loadContentSummary(contentId.value)
  },
  { immediate: true },
)

function handlePicked(item: ContentItem) {
  contentId.value = item.id
  attachedContent.value = item
  pickerOpen.value = false
}

function handleDetach() {
  contentId.value = null
  attachedContent.value = null
}

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    const payload = {
      title: title.value.trim(),
      description: description.value.trim() || null,
      estimated_minutes:
        estimatedMinutes.value === '' ? null : Number(estimatedMinutes.value),
      is_required_for_completion: required.value,
      primary_content_id: contentId.value,
    }
    let result: Lesson
    if (props.lesson) {
      result = await lessonsApi.update(props.lesson.id, payload)
    } else {
      result = await lessonsApi.create(props.moduleId, payload)
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
    :title="lesson ? t('builder.lesson_drawer_edit') : t('builder.lesson_drawer_new')"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
    <form id="lesson-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('builder.field_lesson_title')" required>
        <UiInput v-model="title" required />
      </UiFormField>

      <UiFormField :label="t('builder.field_description')">
        <textarea
          v-model="description"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField :label="t('builder.field_estimated_minutes')">
        <UiInput v-model="estimatedMinutes" type="number" min="0" max="600" />
      </UiFormField>

      <label class="flex items-center gap-2 mb-4 cursor-pointer">
        <input v-model="required" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">{{ t('builder.field_required_for_completion') }}</span>
      </label>

      <div class="mb-4">
        <div class="text-xs font-medium text-foreground mb-2">
          {{ t('builder.field_primary_content') }}
        </div>
        <div
          class="border border-border rounded-md p-3 flex items-center gap-3"
          :class="attachedContent ? 'bg-muted/40' : ''"
        >
          <div class="flex-1 min-w-0">
            <div v-if="attachedContent" class="space-y-1">
              <div class="flex items-center gap-2">
                <UiBadge variant="default">
                  {{ t(`content_picker.type_${attachedContent.type}`) }}
                </UiBadge>
                <span class="text-[13px] font-medium text-foreground truncate">
                  {{ attachedContent.title }}
                </span>
              </div>
              <div
                v-if="attachedContent.description"
                class="text-[12px] text-muted-foreground line-clamp-1"
              >
                {{ attachedContent.description }}
              </div>
            </div>
            <div v-else class="text-[13px] text-muted-foreground italic">
              {{ t('builder.no_content_attached') }}
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <UiButton variant="outline" size="sm" type="button" @click="pickerOpen = true">
              {{ attachedContent ? t('builder.change_content') : t('builder.pick_content') }}
            </UiButton>
            <UiButton
              v-if="attachedContent"
              variant="ghost"
              size="sm"
              type="button"
              class="text-danger-600"
              @click="handleDetach"
            >
              {{ t('builder.remove_content') }}
            </UiButton>
          </div>
        </div>
      </div>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="lesson-form" :loading="submitting">
          {{ lesson ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>

  <ContentPickerDrawer :open="pickerOpen" @close="pickerOpen = false" @picked="handlePicked" />
</template>
