<script setup lang="ts">
/**
 * Phase 6g — Pedagog uchun exam attempts ro'yxati.
 *
 * Har attempt: talaba, status, ball, violation, flagged → review sahifasiga link.
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { attemptsApi, examsApi } from '@shared/api/exams'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import { formatDateTime } from '@shared/utils/datetime'
import type { AttemptPublic, Exam } from '@shared/types/exams'

const { t, locale } = useI18n()

function fmtDateTime(s: string): string {
  return formatDateTime(s, locale.value)
}
const route = useRoute()
const router = useRouter()

const examId = computed(() => Number(route.params.id))
const exam = ref<Exam | null>(null)
const items = ref<AttemptPublic[]>([])
const total = ref(0)
const statusFilter = ref<string>('')
const page = ref(1)
const loading = ref(true)
const error = ref<string | null>(null)

const statusOptions = computed(() => [
  { value: '', label: t('attempt_list.all_statuses') },
  { value: 'in_progress', label: t('exam_result.status_in_progress') },
  { value: 'submitted', label: t('exam_result.status_submitted') },
  { value: 'auto_submitted', label: t('exam_result.status_auto_submitted') },
  { value: 'graded', label: t('exam_result.status_graded') },
  { value: 'flagged', label: t('exam_result.status_flagged') },
  { value: 'invalidated', label: t('exam_result.status_invalidated') },
])

async function load() {
  loading.value = true
  error.value = null
  try {
    if (!exam.value) {
      exam.value = await examsApi.get(examId.value)
    }
    const data = await attemptsApi.listForExam(examId.value, {
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: 50,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

watch([statusFilter, page], load)

function openReview(a: AttemptPublic) {
  router.push({
    name: 'attempt-review',
    params: { id: String(examId.value), attemptId: String(a.id) },
  })
}

function violationVariant(score: number): 'default' | 'warning' | 'danger' {
  if (score >= 80) return 'danger'
  if (score >= 40) return 'warning'
  return 'default'
}

// Phase 8f — CSV export
const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    const blob = await attemptsApi.exportAttemptsCsv(examId.value, {
      status: statusFilter.value || undefined,
    })
    downloadBlob(blob, timestampedFilename(`exam_${examId.value}_attempts`))
    toast.success(t('common.saved'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.load_error')))
  } finally {
    exporting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading && !exam" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="exam">
    <UiBreadcrumb
      :items="[
        t('dashboard.crumb_home'),
        t('exams.tab_exams'),
        exam.title,
        t('attempt_list.title'),
      ]"
      class="mb-6"
    />

    <div class="mb-6 flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="page-title mb-1.5">{{ exam.title }}</h1>
        <p class="page-subtitle">
          {{ t('attempt_list.subtitle', { n: total }) }}
        </p>
      </div>
      <div class="flex items-end gap-2 flex-wrap">
        <UiSelect v-model="statusFilter" :options="statusOptions" />
        <UiButton
          variant="outline"
          :loading="exporting"
          :disabled="items.length === 0"
          @click="exportCsv"
        >
          {{ t('common.export_csv') }}
        </UiButton>
        <UiButton
          variant="outline"
          @click="router.push({ name: 'course-builder', params: { id: exam.course_id } })"
        >
          ← {{ t('attempt_review.back_to_exam') }}
        </UiButton>
      </div>
    </div>

    <UiCard v-if="items.length === 0" class="py-12 text-center text-muted-foreground">
      {{ t('attempt_list.no_attempts') }}
    </UiCard>

    <UiCard v-else no-padding>
      <table class="w-full text-[13px]">
        <thead class="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
          <tr>
            <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('attempt_list.col_user') }}</th>
            <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('attempt_list.col_status') }}</th>
            <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('attempt_list.col_score') }}</th>
            <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('attempt_list.col_pct') }}</th>
            <th scope="col" class="text-right px-4 py-2.5 font-mono">{{ t('attempt_list.col_violation') }}</th>
            <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('attempt_list.col_submitted') }}</th>
            <th scope="col" class="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="a in items" :key="a.id" class="hover:bg-muted/30">
            <td class="px-4 py-3 font-mono">
              #{{ a.user_id }}
              <span class="text-muted-foreground">
                · #{{ a.attempt_number }}
              </span>
            </td>
            <td class="px-4 py-3">
              <UiBadge
                :variant="
                  a.status === 'graded'
                    ? 'success'
                    : a.status === 'invalidated'
                      ? 'warning'
                      : a.flagged
                        ? 'warning'
                        : 'default'
                "
                with-dot
              >
                {{ t(`exam_result.status_${a.status}`) }}
              </UiBadge>
              <UiBadge v-if="a.flagged" variant="warning" class="ml-1">
                ⚑
              </UiBadge>
            </td>
            <td class="px-4 py-3 text-right font-mono">
              {{ a.total_score ?? '—' }} / {{ a.max_score ?? '—' }}
            </td>
            <td class="px-4 py-3 text-right font-mono">{{ a.percentage ?? '—' }}%</td>
            <td class="px-4 py-3 text-right">
              <UiBadge :variant="violationVariant(a.violation_score)">
                {{ a.violation_score }}
              </UiBadge>
            </td>
            <td class="px-4 py-3 font-mono text-[11px] text-muted-foreground">
              {{
                a.submitted_at ? fmtDateTime(a.submitted_at) : '—'
              }}
            </td>
            <td class="px-4 py-3 text-right">
              <UiButton size="sm" variant="ghost" @click="openReview(a)">
                {{ t('attempt_list.review') }} →
              </UiButton>
            </td>
          </tr>
        </tbody>
      </table>
    </UiCard>
  </template>
</template>
