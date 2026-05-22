<script setup lang="ts">
/**
 * Wireframe `.stat-card` — 20px padding, 8px radius, 1px border.
 * `.stat-label` — 11px Geist Mono UPPERCASE, mute, 8px mb
 * `.stat-value` — 28px weight 600, tnum
 * `.stat-trend` — 12px, 4px mt, dot (`.dot`)
 *   up: success, down: destructive
 *
 * `tone` — wireframe 12 dagi "Baholash kutmoqda" yellow card uchun
 *   default | warning | success | danger
 */
interface Props {
  label: string
  value: string | number
  trend?: { direction: 'up' | 'down' | 'flat'; text: string }
  hint?: string
  tone?: 'default' | 'warning' | 'success' | 'danger'
}

withDefaults(defineProps<Props>(), {
  trend: undefined,
  hint: '',
  tone: 'default',
})
</script>

<template>
  <div
    class="border rounded-lg p-5"
    :class="{
      'bg-background border-border': tone === 'default',
      'bg-warning-50 border-warning-200': tone === 'warning',
      'bg-success-50 border-success-200': tone === 'success',
      'bg-danger-50 border-danger-200': tone === 'danger',
    }"
  >
    <div
      class="font-mono text-[11px] uppercase tracking-widest mb-2"
      :class="{
        'text-muted-foreground': tone === 'default',
        'text-warning-700': tone === 'warning',
        'text-success-700': tone === 'success',
        'text-danger-700': tone === 'danger',
      }"
    >{{ label }}</div>
    <div
      class="text-[28px] font-semibold tracking-tight tabular-nums"
      :class="{
        'text-foreground': tone === 'default',
        'text-warning-700': tone === 'warning',
        'text-success-700': tone === 'success',
        'text-danger-700': tone === 'danger',
      }"
    >{{ value }}</div>
    <div
      v-if="trend"
      class="mt-1 text-xs flex items-center gap-1.5"
      :class="{
        'text-success-600': trend.direction === 'up',
        'text-danger-600': trend.direction === 'down',
        'text-muted-foreground': trend.direction === 'flat',
      }"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-current inline-block" aria-hidden="true"></span>
      {{ trend.text }}
    </div>
    <div
      v-else-if="hint"
      class="mt-1 font-mono text-[11px] uppercase tracking-wider"
      :class="
        tone === 'default'
          ? 'text-muted-foreground'
          : tone === 'warning'
            ? 'text-warning-700'
            : tone === 'success'
              ? 'text-success-700'
              : 'text-danger-700'
      "
    >{{ hint }}</div>
  </div>
</template>
