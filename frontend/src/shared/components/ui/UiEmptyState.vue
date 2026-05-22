<script setup lang="ts">
/**
 * Phase 8a — Empty / no-data state.
 *
 * Sodda monoxrom kartochka. Ikkonka slot ixtiyoriy. Action slot orqali
 * CTA tugmasi qo'shish mumkin.
 *
 * Variants:
 *   - default  → no data
 *   - search   → topilmadi (filter natijasi)
 *   - error    → xato (loaddan keyin)
 *   - locked   → ruxsat yo'q
 */

interface Props {
  variant?: 'default' | 'search' | 'error' | 'locked'
  title?: string
  description?: string
  /** Card o'rab turish kerak bo'lmasa false. CourseBuilder kabi joyda. */
  bordered?: boolean
  compact?: boolean
}

withDefaults(defineProps<Props>(), {
  variant: 'default',
  title: '',
  description: '',
  bordered: true,
  compact: false,
})
</script>

<template>
  <div
    :class="[
      'text-center',
      compact ? 'py-8 px-4' : 'py-12 px-6',
      bordered ? 'bg-background border border-dashed border-border rounded-lg' : '',
    ]"
    role="status"
  >
    <div
      class="mx-auto mb-3 w-10 h-10 grid place-items-center rounded-full bg-muted text-muted-foreground"
      aria-hidden="true"
    >
      <slot name="icon">
        <!-- Defaults per variant (SVG inline, no extra deps) -->
        <svg
          v-if="variant === 'search'"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <svg
          v-else-if="variant === 'error'"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <svg
          v-else-if="variant === 'locked'"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        <svg
          v-else
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </slot>
    </div>
    <div v-if="title" class="text-[14px] font-semibold text-foreground mb-1">
      {{ title }}
    </div>
    <div v-if="description" class="text-[12px] text-muted-foreground max-w-md mx-auto">
      {{ description }}
    </div>
    <div v-if="$slots.default" class="text-[13px] text-muted-foreground">
      <slot />
    </div>
    <div v-if="$slots.action" class="mt-4 flex justify-center gap-2">
      <slot name="action" />
    </div>
  </div>
</template>
