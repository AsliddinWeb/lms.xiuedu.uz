<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import { assignmentsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { Assignment, Submission, SubmissionFile } from '@shared/types/assignments'

interface Props {
  assignment: Assignment
  /** Block submit button when no attempts left or pending */
  disabledReason?: string | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ submitted: [submission: Submission] }>()

const { t } = useI18n()

const content = ref('')
const stagedFiles = ref<SubmissionFile[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const submitting = ref(false)
const uploading = ref(false)
const error = ref<string | null>(null)

const allowedHelp = computed(() => {
  const types = props.assignment.allowed_file_types.length
    ? props.assignment.allowed_file_types.join(', ')
    : 'any'
  return t('assignments.submit_help_file', {
    types,
    size: props.assignment.max_file_size_mb,
  })
})

const maxBytes = computed(
  () => props.assignment.max_file_size_mb * 1024 * 1024,
)

function fileExt(name: string): string {
  return name.includes('.') ? name.split('.').pop()!.toLowerCase() : ''
}

async function pickFiles(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  error.value = null
  uploading.value = true
  try {
    const allowed = props.assignment.allowed_file_types.map((x) => x.toLowerCase())
    for (const file of Array.from(target.files)) {
      if (file.size > maxBytes.value) {
        error.value = t('assignments.file_size_too_big', {
          limit: props.assignment.max_file_size_mb,
        })
        continue
      }
      const ext = fileExt(file.name)
      if (allowed.length > 0 && !allowed.includes(ext)) {
        error.value = t('assignments.file_ext_not_allowed', { ext })
        continue
      }
      const uploaded = await assignmentsApi.upload(props.assignment.id, file)
      stagedFiles.value = [...stagedFiles.value, uploaded]
    }
  } catch (e) {
    error.value = extractErrorMessage(e, 'Upload error')
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function removeStaged(idx: number) {
  stagedFiles.value = stagedFiles.value.filter((_, i) => i !== idx)
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const canSubmit = computed(() => {
  if (props.disabledReason) return false
  if (props.assignment.type === 'essay') {
    return content.value.trim().length >= 1
  }
  return stagedFiles.value.length > 0
})

async function handleSubmit() {
  if (!canSubmit.value) return
  error.value = null
  submitting.value = true
  try {
    const payload: { content?: string | null; files?: SubmissionFile[] } = {}
    if (props.assignment.type === 'essay') {
      payload.content = content.value
    } else {
      payload.files = stagedFiles.value
    }
    const sub = await assignmentsApi.submit(props.assignment.id, payload)
    content.value = ''
    stagedFiles.value = []
    emit('submitted', sub)
  } catch (e) {
    error.value = extractErrorMessage(e, 'Submission error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="border border-border rounded-lg p-5 bg-background">
    <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-3">
      {{ t('assignments.submit_section') }}
    </div>

    <UiAlert v-if="disabledReason" variant="warning" class="mb-3">
      {{ disabledReason }}
    </UiAlert>

    <UiAlert v-if="error" variant="danger" class="mb-3">{{ error }}</UiAlert>

    <!-- ESSAY -->
    <template v-if="assignment.type === 'essay'">
      <UiFormField :label="t('assignments.submit_essay_label')">
        <textarea
          v-model="content"
          rows="8"
          :placeholder="t('assignments.submit_essay_placeholder')"
          :disabled="!!disabledReason"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] leading-6 px-3 py-2 outline-none focus:border-foreground focus:shadow-focus disabled:opacity-60 disabled:cursor-not-allowed"
        ></textarea>
        <div class="text-[11px] text-muted-foreground mt-1">
          {{ t('assignments.submit_help_essay') }} · {{ content.length }} chars
        </div>
      </UiFormField>
    </template>

    <!-- FILE -->
    <template v-else>
      <UiFormField :label="t('assignments.submit_files_label')">
        <input
          ref="fileInput"
          type="file"
          multiple
          :disabled="!!disabledReason || uploading"
          class="block w-full text-[13px] text-foreground file:mr-3 file:rounded-md file:border-0 file:bg-foreground file:text-background file:px-3 file:py-1.5 file:text-[12px] file:font-medium file:cursor-pointer disabled:opacity-60"
          @change="pickFiles"
        />
        <div class="text-[11px] text-muted-foreground mt-1">{{ allowedHelp }}</div>
      </UiFormField>

      <div v-if="uploading" class="text-[12px] text-muted-foreground italic mb-3">
        {{ t('assignments.file_uploading') }}
      </div>

      <ul
        v-if="stagedFiles.length > 0"
        class="space-y-1.5 mb-4 border border-border rounded-md divide-y divide-border"
      >
        <li
          v-for="(f, i) in stagedFiles"
          :key="i"
          class="flex items-center gap-3 px-3 py-2"
        >
          <svg width="16" height="16" viewBox="0 0 18 18" fill="none" stroke="currentColor"
            stroke-width="1.5" stroke-linecap="round" class="shrink-0 text-muted-foreground">
            <path d="M3 3h7l5 5v7a2 2 0 0 1-2 2H3z" />
            <path d="M10 3v5h5" />
          </svg>
          <div class="flex-1 min-w-0">
            <div class="text-[13px] truncate">{{ f.name }}</div>
            <div class="font-mono text-[10px] text-muted-foreground">
              {{ f.mime }} · {{ fmtSize(f.size) }}
            </div>
          </div>
          <UiButton
            type="button"
            variant="ghost"
            size="sm"
            class="text-danger-600 shrink-0"
            @click="removeStaged(i)"
          >
            {{ t('assignments.submit_remove_file') }}
          </UiButton>
        </li>
      </ul>
    </template>

    <div class="flex justify-end mt-3">
      <UiButton
        :disabled="!canSubmit || submitting || uploading"
        :loading="submitting"
        @click="handleSubmit"
      >
        {{ t('assignments.submit_button') }}
      </UiButton>
    </div>
  </div>
</template>
