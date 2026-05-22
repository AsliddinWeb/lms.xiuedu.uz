<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useI18n } from 'vue-i18n'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import { useDueCountdown } from '@shared/composables/useDueCountdown'
import type { Assignment } from '@shared/types/assignments'

interface Props {
  assignment: Assignment
}
const props = defineProps<Props>()
defineEmits<{ open: [] }>()

const { t } = useI18n()
const { label: dueLabel, isOverdue } = useDueCountdown(
  toRef(() => props.assignment.due_date),
)

const dueVariant = computed<'default' | 'warning' | 'danger'>(() => {
  if (isOverdue.value) return 'danger'
  return 'default'
})
</script>

<template>
  <button
    type="button"
    class="text-left p-4 border border-border rounded-lg bg-background hover:border-foreground transition-colors"
    @click="$emit('open')"
  >
    <div class="flex items-center gap-2 mb-2">
      <UiBadge variant="default">{{ t(`assignments.type_${assignment.type}`) }}</UiBadge>
      <UiBadge :variant="dueVariant" :with-dot="isOverdue">
        {{ dueLabel }}
      </UiBadge>
    </div>
    <div class="text-[14px] font-semibold text-foreground truncate">
      {{ assignment.title }}
    </div>
    <p
      v-if="assignment.description"
      class="text-[12.5px] text-muted-foreground line-clamp-2 mt-1 leading-5"
    >
      {{ assignment.description }}
    </p>
    <div class="flex items-center gap-3 mt-2 text-[11px] font-mono text-muted-foreground">
      <span>{{ t('assignments.max_score_label') }}: {{ assignment.max_score }}</span>
      <span>·</span>
      <span>
        {{ t('assignments.attempts_value', {
          used: 0,
          max: assignment.max_attempts,
        }) }}
      </span>
    </div>
  </button>
</template>
