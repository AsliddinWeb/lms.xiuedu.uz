<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import UiBadge from '@shared/components/ui/UiBadge.vue'

interface Props {
  /** 0..100 oraliqdagi qiymat (string yoki null) */
  score: string | null
  flagged: boolean
  reportUrl?: string | null
  showReport?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  reportUrl: null,
  showReport: true,
})

const { t } = useI18n()

const value = computed(() => (props.score === null ? null : Number(props.score)))

const variant = computed<'default' | 'warning' | 'danger'>(() => {
  if (props.flagged) return 'danger'
  if (value.value === null) return 'default'
  if (value.value >= 15) return 'warning'
  return 'default'
})
</script>

<template>
  <span class="inline-flex items-center gap-1.5">
    <UiBadge :variant="variant" with-dot>
      <span class="font-mono text-[10px] uppercase mr-1">{{ t('plagiarism.label') }}</span>
      <template v-if="value !== null">
        {{ t('plagiarism.score_label', { n: Math.round(value) }) }}
      </template>
      <template v-else>{{ t('plagiarism.no_check') }}</template>
    </UiBadge>
    <a
      v-if="showReport && reportUrl"
      :href="reportUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="text-[11px] text-muted-foreground hover:text-foreground hover:underline font-mono"
    >
      {{ t('plagiarism.report_link') }} ↗
    </a>
  </span>
</template>
