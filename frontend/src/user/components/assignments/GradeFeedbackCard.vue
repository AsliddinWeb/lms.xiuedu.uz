<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import type { Appeal, Rubric, Submission } from '@shared/types/assignments'

import AppealDrawer from '@user/components/assignments/AppealDrawer.vue'
import PlagiarismBadge from '@user/components/assignments/PlagiarismBadge.vue'

interface Props {
  submission: Submission
  rubric: Rubric | null
  maxScore: string
  /** Talaba shu submission egasi va apellyatsiya berishi mumkin */
  canAppeal?: boolean
  /** Mavjud appellariyatsiya (agar bor bo'lsa, tugma yashirin) */
  myAppeal?: Appeal | null
}
const props = withDefaults(defineProps<Props>(), {
  canAppeal: false,
  myAppeal: null,
})
const emit = defineEmits<{ appealCreated: [appeal: Appeal] }>()

const appealOpen = ref(false)

const { t } = useI18n()

const isReturned = computed(() => props.submission.status === 'returned')

function criterionMax(key: string): number {
  if (!props.rubric) return 0
  const c = props.rubric.criteria.find((x) => x.key === key)
  return Number(c?.max_points ?? 0)
}

function criterionName(key: string): string {
  if (!props.rubric) return key
  const c = props.rubric.criteria.find((x) => x.key === key)
  return c?.name ?? key
}
</script>

<template>
  <div class="border border-border rounded-lg p-5 bg-background">
    <div class="flex flex-wrap items-center gap-2 mb-3">
      <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        {{ t('assignments.grade_section') }}
      </div>
      <UiBadge :variant="isReturned ? 'warning' : 'success'" with-dot>
        {{ t(`assignments.status_${submission.status}`) }}
      </UiBadge>
      <PlagiarismBadge
        v-if="submission.plagiarism_checked_at"
        :score="submission.plagiarism_score"
        :flagged="submission.plagiarism_flagged"
        :report-url="submission.plagiarism_report_url"
      />
      <UiButton
        v-if="canAppeal && !myAppeal"
        variant="outline"
        size="sm"
        class="ml-auto"
        @click="appealOpen = true"
      >
        {{ t('appeals.appeal_button') }}
      </UiButton>
      <UiBadge
        v-else-if="myAppeal"
        :variant="
          myAppeal.status === 'approved'
            ? 'success'
            : myAppeal.status === 'rejected'
              ? 'warning'
              : 'default'
        "
        with-dot
        class="ml-auto"
      >
        {{ t(`appeals.status_${myAppeal.status}`) }}
      </UiBadge>
    </div>

    <AppealDrawer
      :open="appealOpen"
      :submission-id="submission.id"
      @close="appealOpen = false"
      @created="(ap) => emit('appealCreated', ap)"
    />

    <UiAlert v-if="isReturned" variant="warning" class="mb-3">
      {{ t('assignments.grade_returned_msg') }}
    </UiAlert>

    <!-- Score strip -->
    <div class="grid grid-cols-3 gap-3 mb-4">
      <div class="border border-border rounded-md p-3 text-center">
        <div class="font-mono text-[10px] uppercase text-muted-foreground">
          {{ t('assignments.grade_score') }}
        </div>
        <div class="text-lg font-semibold text-foreground mt-0.5">
          {{ submission.score ?? '—' }}
          <span class="text-[12px] font-mono text-muted-foreground">/ {{ maxScore }}</span>
        </div>
      </div>
      <div class="border border-border rounded-md p-3 text-center">
        <div class="font-mono text-[10px] uppercase text-muted-foreground">
          {{ t('assignments.grade_final') }}
        </div>
        <div class="text-lg font-semibold text-foreground mt-0.5">
          {{ submission.final_score ?? '—' }}
        </div>
      </div>
      <div class="border border-border rounded-md p-3 text-center">
        <div class="font-mono text-[10px] uppercase text-muted-foreground">
          {{ t('assignments.grade_letter') }}
        </div>
        <div class="text-lg font-semibold text-foreground mt-0.5">
          {{ submission.grade_letter ?? '—' }}
        </div>
      </div>
    </div>

    <!-- Rubric breakdown -->
    <div
      v-if="rubric && Object.keys(submission.rubric_scores).length > 0"
      class="mb-4"
    >
      <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
        {{ t('assignments.grade_rubric') }}
      </div>
      <div class="space-y-2">
        <div
          v-for="(pts, key) in submission.rubric_scores"
          :key="key"
          class="flex items-center gap-3 text-[13px]"
        >
          <span class="flex-1 truncate">{{ criterionName(String(key)) }}</span>
          <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              class="h-full bg-foreground"
              :style="{
                width: `${
                  criterionMax(String(key)) > 0
                    ? Math.min(100, (Number(pts) / criterionMax(String(key))) * 100)
                    : 0
                }%`,
              }"
            />
          </div>
          <span class="font-mono text-[12px] shrink-0 w-16 text-right">
            {{ pts }} / {{ criterionMax(String(key)) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Feedback -->
    <div v-if="submission.feedback">
      <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
        {{ t('assignments.grade_feedback') }}
      </div>
      <p class="text-[13px] text-foreground leading-6 whitespace-pre-wrap border border-border rounded-md p-3 bg-muted/30">
        {{ submission.feedback }}
      </p>
    </div>
  </div>
</template>
