<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { contentApi } from '@shared/api/content'
import { usersApi } from '@shared/api/users'
import { useAuthStore } from '@shared/stores/auth'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { ContentItem, ContentStatus, ContentType } from '@shared/types/content'

const { t, locale } = useI18n()
const auth = useAuthStore()

const items = ref<ContentItem[]>([])
const authorNames = ref<Record<number, string>>({})
const loading = ref(false)
const error = ref<string | null>(null)
const acting = ref<number | null>(null)

const searchQ = ref('')
const typeFilter = ref<ContentType | ''>('')
const statusFilter = ref<ContentStatus | ''>('')

const typeOptions = computed(() => [
  { value: '' as ContentType | '', label: t('admin_content.all_types') },
  { value: 'text', label: t('content_picker.type_text') },
  { value: 'video', label: t('content_picker.type_video') },
  { value: 'pdf', label: t('content_picker.type_pdf') },
  { value: 'file', label: t('content_picker.type_file') },
  { value: 'link', label: t('content_picker.type_link') },
])

const statusOptions = computed(() => [
  { value: '' as ContentStatus | '', label: t('admin_content.all_statuses') },
  { value: 'draft', label: t('courses.status_draft') },
  { value: 'review', label: 'Review' },
  { value: 'published', label: t('courses.status_published') },
  { value: 'archived', label: t('courses.status_archived') },
])

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await contentApi.list({
      type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
      q: searchQ.value || undefined,
      page_size: 100,
    })
    items.value = data.items

    const authorIds = Array.from(new Set(items.value.map((c) => c.author_id)))
    const missing = authorIds.filter((id) => !(id in authorNames.value))
    await Promise.all(
      missing.map(async (id) => {
        try {
          const u = await usersApi.get(id)
          authorNames.value = { ...authorNames.value, [id]: u.full_name }
        } catch {
          authorNames.value = { ...authorNames.value, [id]: `#${id}` }
        }
      }),
    )
  } catch (e) {
    error.value = extractErrorMessage(e, 'Yuklashda xato')
  } finally {
    loading.value = false
  }
}

onMounted(load)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchQ, typeFilter, statusFilter], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})

function statusVariant(s: ContentStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function authorLabel(c: ContentItem): string {
  return authorNames.value[c.author_id] ?? `#${c.author_id}`
}

function fmtDate(s: string): string {
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    }).format(new Date(s))
  } catch {
    return s.slice(0, 10)
  }
}

async function transition(c: ContentItem, target: ContentStatus) {
  const promptKey =
    target === 'published'
      ? 'admin_content.transition_published_confirm'
      : 'admin_content.transition_archived_confirm'
  const ok = await confirm({
    title: t(promptKey),
    description: c.title,
    variant: target === 'archived' ? 'danger' : 'default',
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  acting.value = c.id
  try {
    await contentApi.transition(c.id, target)
    await load()
    toast.success(t('common.saved'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.save_error'))
    error.value = msg
    toast.error(msg)
  } finally {
    acting.value = null
  }
}

function canPublish(c: ContentItem): boolean {
  return (
    auth.hasPermission('content.publish') &&
    (c.status === 'draft' || c.status === 'review')
  )
}

function canArchive(c: ContentItem): boolean {
  return auth.hasPermission('content.publish') && c.status === 'published'
}
</script>

<template>
  <div class="mb-6">
    <UiBreadcrumb :items="['Admin', t('admin_content.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_content.title') }}</h1>
    <p class="page-subtitle">{{ t('admin_content.subtitle') }}</p>
  </div>

  <UiCard class="mb-4" no-padding>
    <div class="p-4 grid grid-cols-1 md:grid-cols-[1fr_180px_180px] gap-3">
      <input
        v-model="searchQ"
        :placeholder="t('admin_content.search_placeholder')"
        class="rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
      />
      <UiSelect v-model="typeFilter" :options="typeOptions" />
      <UiSelect v-model="statusFilter" :options="statusOptions" />
    </div>
  </UiCard>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('admin_content.no_content') }}
    </div>
    <table v-else class="w-full text-[13px]">
      <thead class="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
        <tr>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_title') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_type') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_author') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_lang') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_version') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_status') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('admin_content.col_updated') }}</th>
          <th scope="col" class="px-4 py-2.5"></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="c in items" :key="c.id" class="hover:bg-muted/30">
          <td class="px-4 py-3">
            <div class="font-medium text-foreground truncate max-w-[280px]">{{ c.title }}</div>
            <div
              v-if="c.description"
              class="text-[11px] text-muted-foreground mt-0.5 line-clamp-1 max-w-[280px]"
            >
              {{ c.description }}
            </div>
          </td>
          <td class="px-4 py-3">
            <UiBadge variant="default">{{ t(`content_picker.type_${c.type}`) }}</UiBadge>
          </td>
          <td class="px-4 py-3">{{ authorLabel(c) }}</td>
          <td class="px-4 py-3 font-mono text-[12px]">{{ c.language }}</td>
          <td class="px-4 py-3 font-mono text-[12px]">v{{ c.version }}</td>
          <td class="px-4 py-3">
            <UiBadge :variant="statusVariant(c.status)" with-dot>
              {{ c.status }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
            {{ fmtDate(c.updated_at) }}
          </td>
          <td class="px-4 py-3 text-right">
            <div class="flex justify-end gap-1.5">
              <a
                v-if="c.file_url"
                :href="c.file_url"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center justify-center rounded-md border border-border-strong bg-background text-foreground hover:bg-muted px-2.5 py-1.5 text-xs font-medium transition-colors"
              >
                {{ t('admin_content.preview') }}
              </a>
              <UiButton
                v-if="canPublish(c)"
                size="sm"
                :loading="acting === c.id"
                @click="transition(c, 'published')"
              >
                {{ t('admin_content.publish') }}
              </UiButton>
              <UiButton
                v-if="canArchive(c)"
                variant="ghost"
                size="sm"
                :loading="acting === c.id"
                @click="transition(c, 'archived')"
              >
                {{ t('admin_content.unpublish') }}
              </UiButton>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </UiCard>
</template>
