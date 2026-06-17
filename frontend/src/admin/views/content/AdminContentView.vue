<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiExportMenu from '@shared/components/ui/UiExportMenu.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import { contentApi } from '@shared/api/content'
import { usersApi } from '@shared/api/users'
import { useAuthStore } from '@shared/stores/auth'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { ExportSpec } from '@shared/utils/export'
import ContentDetailDrawer from '@admin/components/content/ContentDetailDrawer.vue'
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

const page = ref(1)
const pageSize = 20
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const stats = ref({ total: 0, published: 0, draft: 0, review: 0, archived: 0 })
async function loadStats() {
  const count = (status?: ContentStatus) =>
    contentApi.list({ status, page: 1, page_size: 1 }).then((r) => r.total).catch(() => 0)
  const [tot, pub, dr, rev, arc] = await Promise.all([
    count(), count('published'), count('draft'), count('review'), count('archived'),
  ])
  stats.value = { total: tot, published: pub, draft: dr, review: rev, archived: arc }
}

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
  { value: 'draft', label: t('admin_content.status_draft') },
  { value: 'review', label: t('admin_content.status_review') },
  { value: 'published', label: t('admin_content.status_published') },
  { value: 'archived', label: t('admin_content.status_archived') },
])
function statusLabel(s: ContentStatus): string {
  return t(`admin_content.status_${s}`)
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await contentApi.list({
      type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
      q: searchQ.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = data.items
    total.value = data.total

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
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadStats()
  void load()
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchQ, typeFilter, statusFilter], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 250)
})
watch(page, load)

function statusVariant(s: ContentStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

function authorLabel(c: ContentItem): string {
  return authorNames.value[c.author_id] ?? `#${c.author_id}`
}

// CSV eksport — joriy filtr bo'yicha barcha kontent (client-side)
async function buildExport(): Promise<ExportSpec> {
  const all = await contentApi.list({
    type: typeFilter.value || undefined,
    status: statusFilter.value || undefined,
    q: searchQ.value || undefined,
    page: 1,
    page_size: 1000,
  })
  const missing = Array.from(new Set(all.items.map((c) => c.author_id))).filter(
    (id) => !(id in authorNames.value),
  )
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
  const meta: ExportSpec['meta'] = [{ label: t('admin_content.col_title'), value: String(all.total) }]
  if (statusFilter.value) meta.push({ label: t('admin_content.col_status'), value: t(`admin_content.status_${statusFilter.value}`) })
  if (typeFilter.value) meta.push({ label: t('admin_content.col_type'), value: t(`content_picker.type_${typeFilter.value}`) })
  return {
    title: t('admin_content.title'),
    subtitle: t('admin_content.subtitle'),
    filename: 'kontent',
    meta,
    columns: [
      { key: 'title', label: t('admin_content.col_title'), width: 32 },
      { key: 'type', label: t('admin_content.col_type'), width: 16 },
      { key: 'author', label: t('admin_content.col_author'), width: 22 },
      { key: 'lang', label: t('admin_content.col_lang'), width: 10 },
      { key: 'version', label: t('admin_content.col_version'), width: 10 },
      { key: 'status', label: t('admin_content.col_status'), width: 14 },
      { key: 'size', label: t('admin_content.col_size'), width: 12, align: 'right' },
      { key: 'updated', label: t('admin_content.col_updated'), width: 14 },
    ],
    rows: all.items.map((c) => ({
      title: c.title,
      type: t(`content_picker.type_${c.type}`),
      author: authorLabel(c),
      lang: c.language,
      version: `v${c.version}`,
      status: t(`admin_content.status_${c.status}`),
      size: humanFileSize(c.file_size),
      updated: c.updated_at.slice(0, 10),
    })),
  }
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

function fmtDate(s: string): string {
  try {
    return formatDate(s, locale.value, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    })
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

// Detail drawer + moderatsiya
const detailOpen = ref(false)
const selected = ref<ContentItem | null>(null)
function openDetail(c: ContentItem) {
  selected.value = c
  detailOpen.value = true
}

async function onDrawerTransition(status: ContentStatus) {
  if (!selected.value) return
  acting.value = selected.value.id
  try {
    selected.value = await contentApi.transition(selected.value.id, status)
    await load()
    await loadStats()
    toast.success(t('common.saved'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.save_error')))
  } finally {
    acting.value = null
  }
}

async function onDrawerRemove() {
  if (!selected.value) return
  const ok = await confirm({
    title: t('admin_content.delete_confirm'),
    description: selected.value.title,
    variant: 'danger',
    confirmLabel: t('admin_content.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await contentApi.remove(selected.value.id)
    detailOpen.value = false
    await load()
    await loadStats()
    toast.success(t('common.deleted'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.delete_error')))
  }
}
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_content.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('admin_content.title') }}</h1>
      <p class="page-subtitle">{{ t('admin_content.subtitle') }}</p>
    </div>
    <UiExportMenu :build="buildExport" />
  </div>

  <!-- KPI -->
  <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
    <UiStatCard :label="t('admin_content.kpi_total')" :value="String(stats.total)" />
    <UiStatCard :label="t('admin_content.status_published')" :value="String(stats.published)" tone="success" />
    <UiStatCard :label="t('admin_content.status_review')" :value="String(stats.review)" :tone="stats.review > 0 ? 'warning' : 'default'" />
    <UiStatCard :label="t('admin_content.status_draft')" :value="String(stats.draft)" />
    <UiStatCard :label="t('admin_content.status_archived')" :value="String(stats.archived)" />
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
      <thead class="bg-muted text-[11px] uppercase tracking-wider text-muted-foreground">
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
            <div v-if="c.file_size" class="font-mono text-[10px] text-muted-foreground mt-0.5">
              {{ humanFileSize(c.file_size) }}
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
              {{ statusLabel(c.status) }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
            {{ fmtDate(c.updated_at) }}
          </td>
          <td class="px-4 py-3 text-right">
            <div class="flex justify-end gap-1.5">
              <UiButton variant="outline" size="sm" @click="openDetail(c)">
                {{ t('admin_content.view') }}
              </UiButton>
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

    <div
      v-if="items.length > 0"
      class="flex items-center justify-between px-4 py-3 border-t border-border text-[12px] text-muted-foreground"
    >
      <div>
        {{ t('common.total') }}: <span class="font-mono text-foreground">{{ total }}</span> ·
        {{ t('common.page') }} <span class="font-mono text-foreground">{{ page }}</span> /
        <span class="font-mono">{{ totalPages }}</span>
      </div>
      <div class="flex gap-2">
        <UiButton variant="outline" size="sm" :disabled="page <= 1 || loading" @click="page--">← {{ t('common.prev') }}</UiButton>
        <UiButton variant="outline" size="sm" :disabled="page >= totalPages || loading" @click="page++">{{ t('common.next') }} →</UiButton>
      </div>
    </div>
  </UiCard>

  <ContentDetailDrawer
    :open="detailOpen"
    :content="selected"
    :author-name="selected ? authorLabel(selected) : ''"
    :acting="acting === selected?.id"
    @close="detailOpen = false"
    @transition="onDrawerTransition"
    @remove="onDrawerRemove"
  />
</template>
