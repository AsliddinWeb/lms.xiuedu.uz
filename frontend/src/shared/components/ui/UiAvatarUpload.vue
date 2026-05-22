<script setup lang="ts">
import { computed, ref } from 'vue'

import UiButton from '@shared/components/ui/UiButton.vue'

interface Props {
  modelValue: string | null  // joriy avatar URL
  /** Foydalanuvchi initiallari fallback uchun */
  initials?: string
  /** Drag-drop tashqi konteyner uchun */
  disabled?: boolean
  /** Loading holat tashqaridan */
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  initials: '?',
  disabled: false,
  loading: false,
})

const emit = defineEmits<{
  upload: [file: File]
  remove: []
}>()

const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 2 * 1024 * 1024

const dragOver = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)
const localError = ref<string | null>(null)
const previewUrl = ref<string | null>(null)

const displayUrl = computed(() => previewUrl.value || props.modelValue)

function pickFile() {
  if (props.disabled || props.loading) return
  inputRef.value?.click()
}

function validate(file: File): string | null {
  if (!ALLOWED.includes(file.type)) {
    return `Faqat JPG, PNG, WEBP qabul qilinadi (joriy: ${file.type || 'noma\'lum'})`
  }
  if (file.size > MAX_BYTES) {
    return `Fayl 2 MB dan oshmasligi kerak (joriy: ${(file.size / 1024 / 1024).toFixed(2)} MB)`
  }
  return null
}

async function handleFiles(files: FileList | null) {
  localError.value = null
  if (!files || files.length === 0) return
  const file = files[0]
  const err = validate(file)
  if (err) {
    localError.value = err
    return
  }
  // Local preview
  previewUrl.value = URL.createObjectURL(file)
  emit('upload', file)
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  if (props.disabled || props.loading) return
  void handleFiles(e.dataTransfer?.files ?? null)
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (props.disabled || props.loading) return
  dragOver.value = true
}

function onDragLeave() {
  dragOver.value = false
}

function onChange(e: Event) {
  void handleFiles((e.target as HTMLInputElement).files)
  // Reset for re-pick of same file
  ;(e.target as HTMLInputElement).value = ''
}

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
}

defineExpose({ clearPreview })
</script>

<template>
  <div>
    <div class="flex items-center gap-4">
      <!-- Avatar preview -->
      <div
        class="relative w-24 h-24 rounded-full overflow-hidden border border-border bg-muted grid place-items-center"
      >
        <img
          v-if="displayUrl"
          :src="displayUrl"
          alt="avatar"
          class="w-full h-full object-cover"
        />
        <span v-else class="text-2xl font-semibold text-muted-foreground">{{ initials }}</span>
      </div>

      <!-- Drop zone + tugmalar -->
      <div class="flex-1">
        <div
          @click="pickFile"
          @drop="onDrop"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          :class="[
            'border-2 border-dashed rounded-lg px-4 py-3 cursor-pointer transition-colors',
            dragOver
              ? 'border-foreground bg-muted'
              : 'border-border hover:border-border-strong hover:bg-muted/50',
            (disabled || loading) && 'opacity-50 cursor-not-allowed pointer-events-none',
          ]"
        >
          <div class="text-[13px] text-foreground font-medium">
            {{ loading ? 'Yuklanmoqda...' : 'Faylni tashlang yoki bosing' }}
          </div>
          <div class="text-[11px] text-muted-foreground mt-0.5 font-mono">
            JPG · PNG · WEBP · max 2 MB
          </div>
        </div>

        <div class="mt-2 flex items-center gap-2">
          <UiButton variant="outline" size="sm" :disabled="loading" @click="pickFile">
            Faylni tanlash
          </UiButton>
          <UiButton
            v-if="modelValue"
            variant="ghost"
            size="sm"
            class="text-danger-600"
            :disabled="loading"
            @click="emit('remove')"
          >
            O'chirish
          </UiButton>
        </div>

        <p v-if="localError" class="mt-2 text-[11px] text-danger-600">{{ localError }}</p>
      </div>
    </div>

    <input
      ref="inputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="hidden"
      @change="onChange"
    />
  </div>
</template>
