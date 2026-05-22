<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import type { ContentItem } from '@shared/types/content'

interface Props {
  content: ContentItem | null
}
const props = defineProps<Props>()

const { t } = useI18n()

const textBody = computed(() => {
  const data = props.content?.content_data ?? {}
  if (typeof data.plain === 'string') return data.plain
  if (typeof data.body === 'string') return data.body
  // Fallback: show JSON (Phase 3a/3b dan oldindan kelgan)
  return Object.keys(data).length === 0 ? '' : JSON.stringify(data, null, 2)
})

function fileSizeLabel(bytes: number | null | undefined): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div v-if="!content" class="border border-border rounded-lg p-8 text-center text-muted-foreground bg-muted/30">
    {{ t('player.no_content_attached') }}
  </div>

  <div v-else class="border border-border rounded-lg overflow-hidden bg-background">
    <!-- Header -->
    <div class="px-5 py-3 border-b border-border flex items-center gap-2">
      <UiBadge variant="default">
        {{ t(`content_picker.type_${content.type}`) }}
      </UiBadge>
      <span class="text-[14px] font-medium text-foreground truncate">{{ content.title }}</span>
      <span class="ml-auto font-mono text-[11px] text-muted-foreground">v{{ content.version }}</span>
    </div>

    <!-- Body -->
    <div class="p-5">
      <p v-if="content.description" class="text-[13px] text-muted-foreground mb-4 leading-relaxed">
        {{ content.description }}
      </p>

      <!-- TEXT -->
      <template v-if="content.type === 'text'">
        <UiAlert v-if="!textBody" variant="neutral">{{ t('player.text_no_body') }}</UiAlert>
        <pre
          v-else
          class="whitespace-pre-wrap break-words text-[13.5px] leading-7 text-foreground font-sans bg-muted/30 rounded-md p-4 border border-border"
        >{{ textBody }}</pre>
      </template>

      <!-- VIDEO -->
      <template v-else-if="content.type === 'video'">
        <UiAlert v-if="!content.file_url" variant="warning">{{ t('player.video_unavailable') }}</UiAlert>
        <video
          v-else
          :src="content.file_url"
          controls
          preload="metadata"
          class="w-full max-h-[600px] rounded-md border border-border bg-black"
        >
          {{ t('player.video_unavailable') }}
        </video>
      </template>

      <!-- PDF -->
      <template v-else-if="content.type === 'pdf'">
        <UiAlert v-if="!content.file_url" variant="warning">{{ t('player.pdf_unavailable') }}</UiAlert>
        <template v-else>
          <iframe
            :src="content.file_url"
            class="w-full h-[80vh] rounded-md border border-border bg-background"
            :title="content.title"
          ></iframe>
          <div class="mt-3">
            <a
              :href="content.file_url"
              download
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center justify-center gap-2 rounded-md border border-border-strong bg-background text-foreground hover:bg-muted px-2.5 py-1.5 text-xs font-medium transition-colors"
            >
              {{ t('player.file_download') }}
            </a>
          </div>
        </template>
      </template>

      <!-- FILE -->
      <template v-else-if="content.type === 'file'">
        <UiAlert v-if="!content.file_url" variant="warning">{{ t('player.no_content_attached') }}</UiAlert>
        <a
          v-else
          :href="content.file_url"
          target="_blank"
          rel="noopener noreferrer"
          download
          class="inline-flex items-center gap-3 px-4 py-3 border border-border rounded-md hover:bg-muted/40 transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor"
            stroke-width="1.5" stroke-linecap="round">
            <path d="M3 3h7l5 5v7a2 2 0 0 1-2 2H3z" />
            <path d="M10 3v5h5" />
          </svg>
          <span class="text-[13px] font-medium">{{ t('player.file_download') }}</span>
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ content.mime_type }}
            <template v-if="content.file_size"> · {{ fileSizeLabel(content.file_size) }}</template>
          </span>
        </a>
      </template>

      <!-- LINK -->
      <template v-else-if="content.type === 'link'">
        <UiAlert v-if="!content.file_url" variant="warning">{{ t('player.no_content_attached') }}</UiAlert>
        <a
          v-else
          :href="content.file_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-3 px-4 py-3 border border-border rounded-md hover:bg-muted/40 transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor"
            stroke-width="1.5" stroke-linecap="round">
            <path d="M7 11a3 3 0 0 0 4 0l3-3a3 3 0 0 0-4-4l-1 1" />
            <path d="M11 7a3 3 0 0 0-4 0l-3 3a3 3 0 0 0 4 4l1-1" />
          </svg>
          <span class="text-[13px] font-medium">{{ t('player.open_external') }}</span>
          <span class="font-mono text-[11px] text-muted-foreground truncate max-w-[300px]">
            {{ content.file_url }}
          </span>
        </a>
      </template>
    </div>
  </div>
</template>
