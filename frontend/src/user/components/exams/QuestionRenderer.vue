<script setup lang="ts">
/**
 * Phase 6e — Universal question renderer.
 *
 * Savol turiga qarab tegishli forma ko'rsatiladi. AnswerSubmit shaklida v-model.
 * Code va essay uchun Monaco/TipTap o'rniga oddiy textarea — kelajakda almashtirish mumkin.
 */

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { attemptsApi, codeTestCasesApi } from '@shared/api/exams'
import { extractErrorMessage } from '@shared/api/client'
import type {
  AnswerSubmit,
  CodeRunResultItem,
  QuestionStudent,
} from '@shared/types/exams'

interface Props {
  question: QuestionStudent
  modelValue: AnswerSubmit
  disabled?: boolean
  attemptId?: number  // Phase 9d — Run code uchun
}
const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  attemptId: undefined,
})
const emit = defineEmits<{ 'update:modelValue': [v: AnswerSubmit] }>()

const { t } = useI18n()

function update(patch: Partial<AnswerSubmit>) {
  emit('update:modelValue', {
    ...props.modelValue,
    question_id: props.question.id,
    ...patch,
  })
}

const selectedIds = computed(() => props.modelValue.selected_option_ids ?? [])

function toggleSingle(optId: number) {
  if (props.disabled) return
  update({ selected_option_ids: [optId] })
}
function toggleMulti(optId: number) {
  if (props.disabled) return
  const set = new Set(selectedIds.value)
  if (set.has(optId)) set.delete(optId)
  else set.add(optId)
  update({ selected_option_ids: Array.from(set) })
}

const isSingle = computed(() => props.question.type === 'single_choice')
const isMulti = computed(() => props.question.type === 'multiple_choice')
const isTrueFalse = computed(() => props.question.type === 'true_false')
const isShortText = computed(() => props.question.type === 'short_text')
const isEssay = computed(() => props.question.type === 'essay')
const isCode = computed(() => props.question.type === 'code')
const isFileUpload = computed(() => props.question.type === 'file_upload')

const fileSizeMb = computed(() => {
  const b = props.modelValue.file_size_bytes ?? 0
  if (!b) return 0
  return Math.round((b / 1024 / 1024) * 10) / 10
})

// Phase 9d — code "Run" tugmasi
const runningCode = ref(false)
const runResults = ref<CodeRunResultItem[] | null>(null)
const runError = ref<string | null>(null)
const runSummary = ref<{ passed: number; total: number } | null>(null)

async function runCode(): Promise<void> {
  if (!props.attemptId || props.disabled) return
  const code = props.modelValue.code_answer ?? props.question.code_initial ?? ''
  if (!code.trim()) {
    runError.value = t('exam_take.code_empty')
    return
  }
  runningCode.value = true
  runError.value = null
  try {
    const res = await codeTestCasesApi.runForAttempt(
      props.attemptId,
      props.question.id,
      code,
    )
    runResults.value = res.results
    runSummary.value = { passed: res.passed_count, total: res.total }
  } catch (e) {
    runError.value = extractErrorMessage(e, t('exam_take.code_run_error'))
  } finally {
    runningCode.value = false
  }
}

const fileUploading = ref(false)
const fileError = ref<string | null>(null)

async function onFilePick(ev: Event) {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || props.attemptId === undefined) return
  fileError.value = null
  fileUploading.value = true
  try {
    const res = await attemptsApi.uploadFile(props.attemptId, props.question.id, file)
    update({ file_url: res.url, file_size_bytes: res.size })
  } catch (e) {
    fileError.value = extractErrorMessage(e, t('exam_take.file_upload_error'))
  } finally {
    fileUploading.value = false
    target.value = ''
  }
}
</script>

<template>
  <div>
    <!-- Question title + points -->
    <div class="mb-4">
      <div class="flex items-baseline gap-3 mb-2">
        <span class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          {{ t(`exams.qtype_${question.type}`) }}
        </span>
        <span class="font-mono text-[11px] text-muted-foreground">
          {{ question.points }} {{ t('exam_take.pts') }}
        </span>
      </div>
      <h2 class="text-[18px] font-semibold text-foreground leading-snug whitespace-pre-wrap">
        {{ question.title }}
      </h2>
    </div>

    <!-- Single choice / True-false -->
    <div v-if="isSingle || isTrueFalse" class="space-y-2">
      <button
        v-for="opt in question.options"
        :key="opt.id"
        type="button"
        :disabled="disabled"
        class="w-full text-left px-4 py-3 rounded-md border text-[14px] transition-colors disabled:opacity-50"
        :class="
          selectedIds.includes(opt.id)
            ? 'border-foreground bg-muted/60'
            : 'border-border-strong hover:bg-muted/30'
        "
        @click="toggleSingle(opt.id)"
      >
        <span class="inline-flex items-center gap-3">
          <span
            class="inline-block w-4 h-4 rounded-full border-2 grid place-items-center shrink-0"
            :class="
              selectedIds.includes(opt.id)
                ? 'border-foreground'
                : 'border-border-strong'
            "
          >
            <span
              v-if="selectedIds.includes(opt.id)"
              class="w-2 h-2 rounded-full bg-foreground"
            ></span>
          </span>
          <span class="whitespace-pre-wrap">{{ opt.text }}</span>
        </span>
      </button>
    </div>

    <!-- Multiple choice -->
    <div v-else-if="isMulti" class="space-y-2">
      <button
        v-for="opt in question.options"
        :key="opt.id"
        type="button"
        :disabled="disabled"
        class="w-full text-left px-4 py-3 rounded-md border text-[14px] transition-colors disabled:opacity-50"
        :class="
          selectedIds.includes(opt.id)
            ? 'border-foreground bg-muted/60'
            : 'border-border-strong hover:bg-muted/30'
        "
        @click="toggleMulti(opt.id)"
      >
        <span class="inline-flex items-center gap-3">
          <span
            class="inline-block w-4 h-4 rounded border-2 grid place-items-center shrink-0"
            :class="
              selectedIds.includes(opt.id)
                ? 'border-foreground bg-foreground text-background'
                : 'border-border-strong'
            "
          >
            <span v-if="selectedIds.includes(opt.id)" class="text-[12px] leading-none">✓</span>
          </span>
          <span class="whitespace-pre-wrap">{{ opt.text }}</span>
        </span>
      </button>
    </div>

    <!-- Short text -->
    <div v-else-if="isShortText">
      <input
        :value="modelValue.text_answer ?? ''"
        :disabled="disabled"
        type="text"
        :placeholder="t('exam_take.short_text_placeholder')"
        class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[14px] px-3 py-2.5 outline-none focus:border-foreground focus:shadow-focus disabled:opacity-50"
        @input="update({ text_answer: ($event.target as HTMLInputElement).value })"
      />
    </div>

    <!-- Essay -->
    <div v-else-if="isEssay">
      <textarea
        :value="modelValue.text_answer ?? ''"
        :disabled="disabled"
        rows="10"
        :placeholder="t('exam_take.essay_placeholder')"
        class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[14px] px-3 py-2.5 outline-none focus:border-foreground focus:shadow-focus disabled:opacity-50 leading-relaxed"
        @input="update({ text_answer: ($event.target as HTMLTextAreaElement).value })"
      ></textarea>
      <div class="text-[11px] font-mono text-muted-foreground mt-1">
        {{ (modelValue.text_answer ?? '').length }} {{ t('exam_take.chars') }}
      </div>
    </div>

    <!-- Code -->
    <div v-else-if="isCode">
      <div class="flex items-center justify-between mb-1">
        <div class="font-mono text-[11px] text-muted-foreground">
          {{ question.code_language ?? 'plaintext' }}
        </div>
        <button
          v-if="attemptId"
          type="button"
          class="text-[12px] font-mono px-3 py-1 rounded border border-border-strong bg-background hover:bg-muted text-foreground disabled:opacity-50"
          :disabled="disabled || runningCode"
          @click="runCode"
        >
          {{ runningCode ? t('exam_take.code_running') : '▶ ' + t('exam_take.code_run') }}
        </button>
      </div>
      <textarea
        :value="modelValue.code_answer ?? question.code_initial ?? ''"
        :disabled="disabled"
        rows="14"
        spellcheck="false"
        class="block w-full rounded-md border border-border-strong bg-muted/30 text-foreground text-[13px] font-mono px-3 py-2.5 outline-none focus:border-foreground focus:shadow-focus disabled:opacity-50 leading-relaxed"
        @input="update({ code_answer: ($event.target as HTMLTextAreaElement).value })"
      ></textarea>

      <!-- Run results -->
      <div v-if="runError" class="mt-2 text-[12px] text-danger-600 font-mono">
        {{ runError }}
      </div>
      <div v-if="runResults && runSummary" class="mt-3 rounded-md border border-border overflow-hidden">
        <div
          class="px-3 py-2 text-[12px] font-mono"
          :class="
            runSummary.passed === runSummary.total
              ? 'bg-success-500/15 text-success-700'
              : 'bg-warning-500/15 text-warning-700'
          "
        >
          {{ t('exam_take.code_test_summary', {
            passed: runSummary.passed,
            total: runSummary.total,
          }) }}
        </div>
        <ul class="divide-y divide-border">
          <li v-for="(r, idx) in runResults" :key="r.test_case_id" class="px-3 py-2 text-[12px]">
            <div class="flex items-center gap-2 font-mono">
              <span :class="r.passed ? 'text-success-600' : 'text-danger-600'">
                {{ r.passed ? '✓' : '✗' }}
              </span>
              <span>{{ t('exam_take.code_test_n', { n: idx + 1 }) }}</span>
              <span class="text-muted-foreground">· {{ r.runtime_ms }}ms</span>
              <span v-if="r.timed_out" class="text-danger-600">· {{ t('exam_take.code_timeout') }}</span>
              <span v-if="r.exit_code !== 0" class="text-danger-600">· exit={{ r.exit_code }}</span>
            </div>
            <div v-if="!r.passed && r.expected_stdout !== null" class="grid grid-cols-2 gap-2 mt-1.5">
              <div>
                <div class="text-[10px] font-mono uppercase text-muted-foreground">{{ t('exam_take.code_expected') }}</div>
                <pre class="text-[11px] font-mono bg-muted/40 rounded p-1.5 overflow-x-auto whitespace-pre">{{ r.expected_stdout }}</pre>
              </div>
              <div>
                <div class="text-[10px] font-mono uppercase text-muted-foreground">{{ t('exam_take.code_actual') }}</div>
                <pre class="text-[11px] font-mono bg-muted/40 rounded p-1.5 overflow-x-auto whitespace-pre">{{ r.stdout || '(empty)' }}</pre>
              </div>
            </div>
            <div v-if="r.stderr" class="mt-1">
              <pre class="text-[11px] font-mono bg-danger-500/10 text-danger-700 rounded p-1.5 overflow-x-auto whitespace-pre">{{ r.stderr }}</pre>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <!-- File upload -->
    <div v-else-if="isFileUpload">
      <input
        type="file"
        :disabled="disabled"
        :accept="
          question.allowed_file_types
            ? question.allowed_file_types.map((t) => '.' + t).join(',')
            : undefined
        "
        class="block w-full text-[13px] file:mr-3 file:px-3 file:py-2 file:rounded-md file:border file:border-border-strong file:bg-background file:text-foreground file:cursor-pointer disabled:opacity-50"
        @change="onFilePick"
      />
      <div v-if="fileUploading" class="text-[12px] text-muted-foreground mt-2 italic">
        {{ t('exam_take.file_uploading') }}
      </div>
      <div v-else-if="fileError" class="text-[12px] text-danger-600 mt-2">
        {{ fileError }}
      </div>
      <a
        v-else-if="modelValue.file_url"
        :href="modelValue.file_url"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-2 text-[12px] text-success mt-2 hover:underline"
      >
        ✓ {{ t('exam_take.file_uploaded') }} · {{ fileSizeMb }} MB
      </a>
      <div class="text-[11px] text-muted-foreground mt-2">
        {{ t('exam_take.file_upload_note') }}
        <span v-if="question.max_file_size_mb">
          · max {{ question.max_file_size_mb }} MB
        </span>
        <span v-if="question.allowed_file_types?.length">
          · {{ question.allowed_file_types.join(', ') }}
        </span>
      </div>
    </div>
  </div>
</template>
