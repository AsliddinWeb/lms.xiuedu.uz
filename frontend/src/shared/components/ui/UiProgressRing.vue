<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** 0-100 oralig'idagi qiymat */
  percent: number | string
  /** Halqa diametri (px) */
  size?: number
  /** Halqa qalinligi (px) */
  thickness?: number
  /** Markazdagi label — odatiy ravishda foiz ko'rsatadi. label=false bo'lsa hech narsa chiqmaydi. */
  showLabel?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 56,
  thickness: 5,
  showLabel: true,
})

const value = computed(() => {
  const v = typeof props.percent === 'string' ? parseFloat(props.percent) : props.percent
  if (Number.isNaN(v)) return 0
  return Math.max(0, Math.min(100, v))
})

const radius = computed(() => (props.size - props.thickness) / 2)
const circ = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circ.value * (1 - value.value / 100))
const isComplete = computed(() => value.value >= 100)
</script>

<template>
  <div
    class="relative inline-grid place-items-center"
    :style="{ width: `${size}px`, height: `${size}px` }"
  >
    <svg :width="size" :height="size" class="-rotate-90">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        :stroke-width="thickness"
        fill="none"
        class="stroke-muted"
      />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        :stroke-width="thickness"
        fill="none"
        stroke-linecap="round"
        :stroke-dasharray="circ"
        :stroke-dashoffset="offset"
        class="transition-all duration-500"
        :class="isComplete ? 'stroke-success-500' : 'stroke-foreground'"
      />
    </svg>
    <div v-if="showLabel" class="absolute inset-0 grid place-items-center">
      <span class="font-mono text-[11px] font-medium text-foreground">
        {{ Math.round(value) }}%
      </span>
    </div>
  </div>
</template>
