<script setup lang="ts">
/**
 * Wireframe `.video-placeholder` — dark (#18181b), 16/9, white play button center.
 * Used in lesson player when video not yet loaded.
 */
interface Props {
  label?: string  // bottom label, e.g. "VIDEO PLAYER · HLS · 1080p"
}
withDefaults(defineProps<Props>(), { label: 'VIDEO' })
</script>

<template>
  <div
    class="bg-[#18181b] text-[#71717a] grid place-items-center rounded-md relative"
    style="aspect-ratio: 16/9;"
  >
    <div class="flex flex-col items-center gap-4">
      <div
        class="w-14 h-14 rounded-full border-2 border-white/30 bg-white/10 grid place-items-center text-white"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path d="M5 3v14l12-7z" />
        </svg>
      </div>
      <div class="font-mono text-[11px] text-white/40 uppercase tracking-widest text-center">
        {{ label }}
      </div>
    </div>
  </div>
</template>
