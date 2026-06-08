<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import type { Submission, SubmissionStatus } from '@shared/types/assignments'

import PlagiarismBadge from '@user/components/assignments/PlagiarismBadge.vue'

interface Props {
  submissions: Submission[]
}
defineProps<Props>()

const { t, locale } = useI18n()

function fmtDateTime(s: string): string {
  try {
    return formatDate(s, locale.value, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return s
  }
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function statusVariant(s: SubmissionStatus): 'default' | 'success' | 'warning' {
  if (s === 'graded') return 'success'
  if (s === 'returned') return 'warning'
  return 'default'
}
</script>

<template>
  <div>
    <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-3">
      {{ t('assignments.history_section') }}
    </div>

    <div
      v-if="submissions.length === 0"
      class="text-[13px] text-muted-foreground italic py-6 text-center border border-border rounded-lg"
    >
      {{ t('assignments.history_empty') }}
    </div>

    <ol v-else class="space-y-3">
      <li
        v-for="s in submissions"
        :key="s.id"
        class="border border-border rounded-lg p-4 bg-background"
      >
        <div class="flex items-center gap-2 mb-2">
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ t('assignments.attempt_label', { n: s.attempt_number }) }}
          </span>
          <UiBadge :variant="statusVariant(s.status)" with-dot>
            {{ t(`assignments.status_${s.status}`) }}
          </UiBadge>
          <UiBadge v-if="s.is_late" variant="warning">
            {{ t('assignments.days_late_label', { n: s.days_late }) }}
          </UiBadge>
          <PlagiarismBadge
            v-if="s.plagiarism_checked_at"
            :score="s.plagiarism_score"
            :flagged="s.plagiarism_flagged"
            :report-url="s.plagiarism_report_url"
            :show-report="false"
          />
          <span class="ml-auto font-mono text-[11px] text-muted-foreground">
            {{ fmtDateTime(s.submitted_at) }}
          </span>
        </div>

        <p
          v-if="s.content"
          class="text-[13px] text-foreground leading-6 whitespace-pre-wrap mb-2"
        >
          {{ s.content }}
        </p>

        <div v-if="s.files.length > 0" class="space-y-1 mb-2">
          <a
            v-for="(f, i) in s.files"
            :key="i"
            :href="f.url"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center gap-2 text-[13px] hover:underline"
          >
            <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor"
              stroke-width="1.5" stroke-linecap="round" class="text-muted-foreground">
              <path d="M3 3h7l5 5v7a2 2 0 0 1-2 2H3z" />
              <path d="M10 3v5h5" />
            </svg>
            <span class="font-medium">{{ f.name }}</span>
            <span class="font-mono text-[10px] text-muted-foreground">
              {{ fmtSize(f.size) }}
            </span>
          </a>
        </div>

        <!-- Grade strip -->
        <div
          v-if="s.score !== null"
          class="mt-3 pt-3 border-t border-border flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px]"
        >
          <span class="font-mono text-muted-foreground">
            {{ t('assignments.grade_score') }}:
            <span class="text-foreground font-semibold">{{ s.score }}</span>
          </span>
          <span v-if="s.final_score !== null" class="font-mono text-muted-foreground">
            {{ t('assignments.grade_final') }}:
            <span class="text-foreground font-semibold">{{ s.final_score }}</span>
          </span>
          <span v-if="s.grade_letter" class="font-mono text-muted-foreground">
            {{ t('assignments.grade_letter') }}:
            <span class="text-foreground font-semibold">{{ s.grade_letter }}</span>
          </span>
        </div>
        <p
          v-if="s.feedback"
          class="text-[12.5px] text-muted-foreground italic leading-5 mt-2"
        >
          {{ s.feedback }}
        </p>
      </li>
    </ol>
  </div>
</template>
