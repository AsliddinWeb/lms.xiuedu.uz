<script setup lang="ts">
/**
 * Phase 8a — Skeleton loader (shimmer placeholder).
 *
 * Usage:
 *   <UiSkeleton />                         <!-- one line, default h-4 -->
 *   <UiSkeleton variant="card" :count="3"/> <!-- card placeholders -->
 *   <UiSkeleton variant="row" :count="5"/>  <!-- table rows -->
 *
 * Animatsiya tailwind `animate-pulse` orqali. CSS variable'larga binoan
 * light/dark mode'da to'g'ri ko'rinadi (muted background).
 */

interface Props {
  variant?: 'line' | 'card' | 'row' | 'avatar' | 'block'
  count?: number
  /** Tailwind height utility, default variant'ga qarab tanlanadi */
  height?: string
  /** Tailwind width utility, default 'w-full' */
  width?: string
  rounded?: 'sm' | 'md' | 'lg' | 'full'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'line',
  count: 1,
  height: '',
  width: 'w-full',
  rounded: 'md',
})

const heightCls = props.height
  ? props.height
  : {
      line: 'h-4',
      card: 'h-32',
      row: 'h-12',
      avatar: 'h-10 w-10',
      block: 'h-24',
    }[props.variant]

const roundedCls = {
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
}[props.variant === 'avatar' ? 'full' : props.rounded]

const widthCls = props.variant === 'avatar' ? '' : props.width
</script>

<template>
  <div
    v-if="count === 1"
    :class="['bg-muted animate-pulse', heightCls, widthCls, roundedCls]"
    aria-busy="true"
    aria-hidden="true"
  ></div>
  <div v-else class="space-y-2" aria-busy="true" aria-hidden="true">
    <div
      v-for="i in count"
      :key="i"
      :class="['bg-muted animate-pulse', heightCls, widthCls, roundedCls]"
    ></div>
  </div>
</template>
