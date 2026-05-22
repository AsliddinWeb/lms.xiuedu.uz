<script setup lang="ts">
/**
 * Wireframe `.progress` — 6px height, muted bg, 3px radius
 * `.progress-bar` — foreground bg
 */
interface Props {
  value: number  // 0–100
  size?: 'sm' | 'md'
}
withDefaults(defineProps<Props>(), { size: 'md' })
</script>

<template>
  <div
    class="bg-muted rounded-full overflow-hidden w-full"
    :class="size === 'sm' ? 'h-1' : 'h-1.5'"
  >
    <div
      class="bg-foreground h-full rounded-full transition-all"
      :style="{ width: `${Math.min(100, Math.max(0, value))}%` }"
    ></div>
  </div>
</template>
