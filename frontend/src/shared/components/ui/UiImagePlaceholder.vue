<script setup lang="ts">
/**
 * Wireframe `.image-placeholder` — muted bg, 1px border, 45deg fine line pattern
 * + center label badge.
 */
interface Props {
  label?: string
  aspect?: string  // e.g. "16/9", "1/1"
}
withDefaults(defineProps<Props>(), { label: 'IMAGE', aspect: '16/9' })
</script>

<template>
  <div
    class="bg-muted border border-border grid place-items-center text-muted-foreground font-mono text-[11px] rounded-md relative overflow-hidden"
    :style="{ aspectRatio: aspect }"
  >
    <div
      class="absolute inset-0 pointer-events-none"
      style="background-image: linear-gradient(45deg, transparent 48%, var(--border) 49%, var(--border) 51%, transparent 52%);"
    ></div>
    <span class="relative z-10 bg-muted px-2.5 py-1 uppercase tracking-widest">
      {{ label }}
    </span>
  </div>
</template>
