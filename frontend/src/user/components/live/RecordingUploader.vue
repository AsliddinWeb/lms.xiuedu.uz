<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import type { LiveSession } from '@shared/types/live'

interface Props {
  sessionId: number
}
const props = defineProps<Props>()
const emit = defineEmits<{ uploaded: [session: LiveSession] }>()

const { t } = useI18n()

const fileInput = ref<HTMLInputElement | null>(null)
const selected = ref<File | null>(null)
const uploading = ref(false)
const progress = ref<number>(0)
const errorMsg = ref<string | null>(null)

const ALLOWED = [
  'video/mp4',
  'video/webm',
  'video/x-matroska',
  'video/quicktime',
]

const sizeLabel = computed(() => {
  if (!selected.value) return ''
  const mb = selected.value.size / (1024 * 1024)
  return mb < 1
    ? `${(selected.value.size / 1024).toFixed(0)} KB`
    : `${mb.toFixed(1)} MB`
})

function onPickFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  errorMsg.value = null
  const target = e.target as HTMLInputElement
  const f = target.files?.[0]
  if (!f) {
    selected.value = null
    return
  }
  if (!ALLOWED.includes(f.type)) {
    errorMsg.value = t('live.recording_error_format')
    selected.value = null
    return
  }
  selected.value = f
}

async function upload() {
  if (!selected.value) return
  uploading.value = true
  progress.value = 0
  errorMsg.value = null
  try {
    const session = await liveSessionsApi.uploadRecording(
      props.sessionId,
      selected.value,
      (loaded, total) => {
        progress.value = Math.round((loaded / total) * 100)
      },
    )
    emit('uploaded', session)
    selected.value = null
    if (fileInput.value) fileInput.value.value = ''
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('live.recording_error_upload'))
  } finally {
    uploading.value = false
    progress.value = 0
  }
}
</script>

<template>
  <div>
    <UiAlert v-if="errorMsg" variant="danger" class="mb-3">{{ errorMsg }}</UiAlert>

    <input
      ref="fileInput"
      type="file"
      class="hidden"
      accept="video/mp4,video/webm,video/x-matroska,video/quicktime"
      @change="onFileChange"
    />

    <div class="flex flex-col gap-3">
      <p class="text-[13px] text-muted-foreground">
        {{ t('live.recording_upload_hint') }}
      </p>

      <div class="flex items-center gap-3">
        <UiButton variant="outline" :disabled="uploading" @click="onPickFile">
          {{ selected ? t('live.recording_change_file') : t('live.recording_pick_file') }}
        </UiButton>
        <span v-if="selected" class="font-mono text-[12px] text-muted-foreground truncate">
          {{ selected.name }} · {{ sizeLabel }}
        </span>
      </div>

      <div v-if="uploading" class="space-y-1">
        <div class="h-2 bg-muted rounded overflow-hidden">
          <div
            class="h-full bg-foreground transition-all"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>
        <div class="font-mono text-[11px] text-muted-foreground">
          {{ t('live.recording_uploading', { pct: progress }) }}
        </div>
      </div>

      <div v-if="selected && !uploading">
        <UiButton :loading="uploading" @click="upload">
          {{ t('live.recording_upload_btn') }}
        </UiButton>
      </div>
    </div>
  </div>
</template>
