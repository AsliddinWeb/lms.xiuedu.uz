<script setup lang="ts">
/**
 * Admin — kontent tafsilotlari (read-only) + moderatsiya amallari.
 * Pedagog kontentni yuklaydi; admin ko'rib chiqadi, nashr/arxiv/o'chirish qiladi.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import type { ContentItem, ContentStatus } from '@shared/types/content'

interface Props {
  open: boolean
  content: ContentItem | null
  authorName?: string
  acting?: boolean
}
const props = withDefaults(defineProps<Props>(), { authorName: '', acting: false })
const emit = defineEmits<{
  close: []
  transition: [status: ContentStatus]
  remove: []
}>()

const { t, locale } = useI18n()

function statusVariant(s: ContentStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function humanFileSize(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let v = bytes / 1024
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(1)} ${units[i]}`
}

function humanDuration(sec: number | null): string {
  if (sec == null) return '—'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function fmt(s: string | null | undefined): string {
  if (!s) return '—'
  return formatDate(s, locale.value, { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// status'ga qarab mavjud moderatsiya amallari
const canPublish = computed(
  () => props.content && (props.content.status === 'draft' || props.content.status === 'review'),
)
const canArchive = computed(() => props.content?.status === 'published')
const canRestore = computed(() => props.content?.status === 'archived')
</script>

<template>
  <UiDrawer :open="open" :title="t('admin_content.detail_title')" width="lg" @close="emit('close')">
    <template v-if="content">
      <!-- Sarlavha + status -->
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-2 flex-wrap">
          <UiBadge variant="default">{{ t(`content_picker.type_${content.type}`) }}</UiBadge>
          <UiBadge :variant="statusVariant(content.status)" with-dot>
            {{ t(`admin_content.status_${content.status}`) }}
          </UiBadge>
          <span class="font-mono text-[11px] text-muted-foreground">v{{ content.version }}</span>
        </div>
        <h3 class="text-[15px] font-semibold text-foreground">{{ content.title }}</h3>
        <p v-if="content.description" class="text-[13px] text-muted-foreground mt-1">
          {{ content.description }}
        </p>
      </div>

      <!-- Metadata -->
      <div class="mono-tag mb-2">{{ t('admin_content.f_meta') }}</div>
      <dl class="text-[13px] grid grid-cols-2 gap-x-6 gap-y-2 mb-5">
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('admin_content.col_author') }}</dt>
          <dd class="truncate">{{ authorName || `#${content.author_id}` }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('admin_content.col_lang') }}</dt>
          <dd class="font-mono">{{ content.language }}</dd>
        </div>
        <div v-if="content.duration_seconds != null" class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('admin_content.f_duration') }}</dt>
          <dd class="font-mono">{{ humanDuration(content.duration_seconds) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('admin_content.f_created') }}</dt>
          <dd class="font-mono text-[11px]">{{ fmt(content.created_at) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">{{ t('admin_content.col_updated') }}</dt>
          <dd class="font-mono text-[11px]">{{ fmt(content.updated_at) }}</dd>
        </div>
      </dl>

      <!-- Fayl -->
      <template v-if="content.file_url">
        <div class="mono-tag mb-2">{{ t('admin_content.f_file') }}</div>
        <dl class="text-[13px] grid grid-cols-2 gap-x-6 gap-y-2 mb-3">
          <div v-if="content.mime_type" class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('admin_content.f_mime') }}</dt>
            <dd class="font-mono text-[11px]">{{ content.mime_type }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('admin_content.col_size') }}</dt>
            <dd class="font-mono">{{ humanFileSize(content.file_size) }}</dd>
          </div>
        </dl>
        <a
          :href="content.file_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center rounded-md border border-border-strong bg-background text-foreground hover:bg-muted px-3 py-1.5 text-xs font-medium transition-colors mb-5"
        >
          {{ t('admin_content.preview') }} ↗
        </a>
      </template>

      <!-- Teglar -->
      <div class="mono-tag mb-2">{{ t('admin_content.f_tags') }}</div>
      <div class="flex flex-wrap gap-1.5">
        <UiBadge v-for="tag in content.tags" :key="tag" variant="default">{{ tag }}</UiBadge>
        <span v-if="content.tags.length === 0" class="text-[12px] text-muted-foreground italic">
          {{ t('admin_content.f_no_tags') }}
        </span>
      </div>
    </template>

    <template #footer>
      <div class="flex items-center justify-between gap-2 w-full">
        <UiButton
          v-permission="'content.publish'"
          variant="ghost"
          size="sm"
          class="text-danger-600"
          @click="emit('remove')"
        >
          {{ t('admin_content.delete') }}
        </UiButton>
        <div class="flex items-center gap-2">
          <UiButton variant="outline" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
          <UiButton
            v-if="canRestore"
            v-permission="'content.publish'"
            :loading="acting"
            @click="emit('transition', 'draft')"
          >
            {{ t('admin_content.action_restore') }}
          </UiButton>
          <UiButton
            v-if="canArchive"
            v-permission="'content.publish'"
            variant="outline"
            :loading="acting"
            @click="emit('transition', 'archived')"
          >
            {{ t('admin_content.action_archive') }}
          </UiButton>
          <UiButton
            v-if="canPublish"
            v-permission="'content.publish'"
            :loading="acting"
            @click="emit('transition', 'published')"
          >
            {{ t('admin_content.publish') }}
          </UiButton>
        </div>
      </div>
    </template>
  </UiDrawer>
</template>
