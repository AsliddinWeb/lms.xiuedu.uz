<script setup lang="ts">
interface Props {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  withDot?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  withDot: false,
})

const variantClass = {
  default: 'bg-muted text-foreground border-border',
  success:
    'bg-success-50 text-success-700 border-success-200 dark:bg-success-700/15 dark:text-success-200 dark:border-success-700/40',
  warning:
    'bg-warning-50 text-warning-700 border-warning-200 dark:bg-warning-700/15 dark:text-warning-200 dark:border-warning-700/40',
  danger:
    'bg-danger-50 text-danger-700 border-danger-200 dark:bg-danger-700/15 dark:text-danger-200 dark:border-danger-700/40',
  info: 'bg-info-50 text-info-700 border-info-200 dark:bg-info-700/15 dark:text-info-200 dark:border-info-700/40',
}[props.variant]
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 rounded border px-1.5 py-0.5',
      'font-mono text-[11px] font-medium',
      variantClass,
    ]"
  >
    <span v-if="withDot" class="w-1.5 h-1.5 rounded-full bg-current"></span>
    <slot />
  </span>
</template>
