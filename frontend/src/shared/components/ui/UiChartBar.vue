<script setup lang="ts">
/**
 * Wireframe `.chart-bar` — flex columns, 200px height, foreground bars.
 * Simple bar chart for dashboard widgets. Values 0–100.
 */
interface BarItem {
  label: string
  value: number  // 0–100
}
interface Props {
  items: BarItem[]
  height?: number  // total height in px
}
withDefaults(defineProps<Props>(), { height: 200 })
</script>

<template>
  <div
    class="flex items-end gap-1 py-4"
    :style="{ height: `${height}px` }"
  >
    <div
      v-for="(item, i) in items"
      :key="i"
      class="flex-1 bg-foreground rounded-t-sm min-h-[4px] relative hover:opacity-70 transition-opacity"
      :style="{ height: `${Math.max(2, item.value)}%` }"
      :title="`${item.label}: ${item.value}`"
    >
      <div
        class="absolute -bottom-5 left-1/2 -translate-x-1/2 font-mono text-[10px] text-muted-foreground whitespace-nowrap"
      >
        {{ item.label }}
      </div>
    </div>
  </div>
</template>
