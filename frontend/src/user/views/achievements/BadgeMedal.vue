<script setup lang="ts">
/**
 * Nishon medali — kategoriya bo'yicha premium SVG ikonka (emoji yo'q).
 * earned=true: navy/gold medallion; aks holda muted (qulflangan).
 */
defineProps<{ category: string; earned: boolean; size?: number }>()
</script>

<template>
  <div
    class="rounded-full grid place-items-center shrink-0 ring-1 transition-colors"
    :class="
      earned
        ? 'text-[#1f3a5f] bg-gradient-to-br from-[#f3e6c4] to-[#d3a945] ring-[#c19a3e]/50 shadow-sm'
        : 'text-muted-foreground bg-muted ring-border'
    "
    :style="{ width: `${size ?? 48}px`, height: `${size ?? 48}px` }"
  >
    <svg
      :width="(size ?? 48) * 0.5"
      :height="(size ?? 48) * 0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <!-- achievement: kubok -->
      <template v-if="category === 'achievement'">
        <path d="M7 4h10v4a5 5 0 0 1-10 0V4Z" />
        <path d="M7 6H4v1.5A3.5 3.5 0 0 0 7 11M17 6h3v1.5A3.5 3.5 0 0 1 17 11" />
        <path d="M12 13v4M8.5 21h7M9.5 21a2.5 2.5 0 0 1 5 0" />
      </template>
      <!-- mastery: medal -->
      <template v-else-if="category === 'mastery'">
        <circle cx="12" cy="9" r="5.5" />
        <path d="m9.2 13.4-2.2 6.8 5-2.9 5 2.9-2.2-6.8" />
        <path d="m12 6.4 1 2 2.2.3-1.6 1.5.4 2.2-2-1.1-2 1.1.4-2.2-1.6-1.5 2.2-.3 1-2Z" />
      </template>
      <!-- social: chat -->
      <template v-else-if="category === 'social'">
        <path d="M21 14a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2v8Z" />
        <path d="M8 9h8M8 12.5h5" />
      </template>
      <!-- progress (default): bayroq -->
      <template v-else>
        <path d="M5 21V4" />
        <path d="M5 4h11l-1.6 3.2L16 11H5" />
      </template>
    </svg>
  </div>
</template>
