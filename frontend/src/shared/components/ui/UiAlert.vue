<script setup lang="ts">
interface Props {
  variant?: 'info' | 'success' | 'warning' | 'danger' | 'neutral'
}

const props = withDefaults(defineProps<Props>(), { variant: 'neutral' })

// Light va dark rejim uchun alohida tonlar.
// Pattern: dark mode'da soft "tinted" muted bg + brighter text.
const variantClass = {
  info: 'bg-info-50 text-info-700 border-info-200 dark:bg-info-700/15 dark:text-info-200 dark:border-info-700/40',
  success:
    'bg-success-50 text-success-700 border-success-200 dark:bg-success-700/15 dark:text-success-200 dark:border-success-700/40',
  warning:
    'bg-warning-50 text-warning-700 border-warning-200 dark:bg-warning-700/15 dark:text-warning-200 dark:border-warning-700/40',
  danger:
    'bg-danger-50 text-danger-700 border-danger-200 dark:bg-danger-700/15 dark:text-danger-200 dark:border-danger-700/40',
  neutral: 'bg-muted text-foreground border-border',
}[props.variant]
</script>

<template>
  <div :class="['rounded-md border px-3 py-2 text-[13px]', variantClass]">
    <slot />
  </div>
</template>
