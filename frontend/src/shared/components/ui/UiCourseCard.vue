<script setup lang="ts">
/**
 * Wireframe `.course-card` (05-courses-list, 04-student-dashboard).
 * 16/9 cover, kategoriya tag, title, stats, progress bar.
 *
 * Slot'lar:
 *  - cover: agar cover_image_url bo'lmasa <UiImagePlaceholder> default
 *  - actions: pastki action panel uchun
 */
import UiImagePlaceholder from '@shared/components/ui/UiImagePlaceholder.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'

interface CourseStat {
  icon?: string  // emoji or symbol
  label: string
}

interface Props {
  coverUrl?: string | null
  category?: string  // e.g. "Algoritmlar"
  title: string
  stats?: CourseStat[]
  progress?: number | null  // 0–100, null = not started
  clickable?: boolean
}
withDefaults(defineProps<Props>(), {
  coverUrl: null,
  category: '',
  stats: () => [],
  progress: null,
  clickable: true,
})
</script>

<template>
  <article
    class="bg-card border border-border rounded-lg overflow-hidden transition-all"
    :class="
      clickable
        ? 'cursor-pointer hover:border-border-strong hover:-translate-y-0.5'
        : ''
    "
  >
    <!-- Cover -->
    <div class="aspect-video bg-muted relative overflow-hidden">
      <slot name="cover">
        <img
          v-if="coverUrl"
          :src="coverUrl"
          :alt="title"
          class="w-full h-full object-cover"
        />
        <UiImagePlaceholder v-else label="COVER" />
      </slot>
    </div>

    <!-- Meta -->
    <div class="p-4">
      <div
        v-if="category"
        class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2"
      >
        {{ category }}
      </div>
      <h3 class="text-[14px] font-semibold leading-snug mb-2 line-clamp-2">
        {{ title }}
      </h3>

      <div v-if="stats.length > 0" class="flex gap-3 text-[11px] text-muted-foreground mb-3">
        <span v-for="(s, i) in stats" :key="i" class="inline-flex items-center gap-1">
          <span v-if="s.icon">{{ s.icon }}</span>
          <span>{{ s.label }}</span>
        </span>
      </div>

      <UiProgressBar v-if="progress !== null" :value="progress" />

      <slot name="actions" />
    </div>
  </article>
</template>
