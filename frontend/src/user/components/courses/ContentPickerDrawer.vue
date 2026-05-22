<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { contentApi } from '@shared/api/content'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { ContentItem, ContentStatus, ContentType } from '@shared/types/content'

interface Props {
  open: boolean
}
const props = defineProps<Props>()
const emit = defineEmits<{ close: []; picked: [item: ContentItem] }>()

const { t } = useI18n()
const auth = useAuthStore()

type Tab = 'existing' | 'create'
const tab = ref<Tab>('existing')

const items = ref<ContentItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQ = ref('')
const typeFilter = ref<ContentType | ''>('')
const statusFilter = ref<ContentStatus | ''>('')

// Create-form state
const newType = ref<ContentType>('text')
const newTitle = ref('')
const newDescription = ref('')
const newLinkUrl = ref('')
const newTextBody = ref('')
const submitting = ref(false)

const typeOptions = computed(() => [
  { value: '' as ContentType | '', label: t('content_picker.all_types') },
  { value: 'text', label: t('content_picker.type_text') },
  { value: 'video', label: t('content_picker.type_video') },
  { value: 'pdf', label: t('content_picker.type_pdf') },
  { value: 'file', label: t('content_picker.type_file') },
  { value: 'link', label: t('content_picker.type_link') },
])

const statusOptions = computed(() => [
  { value: '' as ContentStatus | '', label: t('content_picker.all_statuses') },
  { value: 'draft', label: t('courses.status_draft') },
  { value: 'review', label: 'Review' },
  { value: 'published', label: t('courses.status_published') },
  { value: 'archived', label: t('courses.status_archived') },
])

const newTypeOptions = computed(() => [
  { value: 'text', label: t('content_picker.type_text') },
  { value: 'link', label: t('content_picker.type_link') },
  { value: 'pdf', label: t('content_picker.type_pdf') },
  { value: 'video', label: t('content_picker.type_video') },
  { value: 'file', label: t('content_picker.type_file') },
])

async function load() {
  if (!auth.user) return
  loading.value = true
  error.value = null
  try {
    const data = await contentApi.list({
      author_id: auth.user.id,
      type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
      q: searchQ.value || undefined,
      page_size: 100,
    })
    items.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, 'Yuklashda xato')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      tab.value = 'existing'
      error.value = null
      newTitle.value = ''
      newDescription.value = ''
      newLinkUrl.value = ''
      newTextBody.value = ''
      newType.value = 'text'
      load()
    }
  },
)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchQ, typeFilter, statusFilter], () => {
  if (!props.open) return
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 200)
})

function pick(item: ContentItem) {
  emit('picked', item)
}

async function createAndAttach() {
  error.value = null
  submitting.value = true
  try {
    const payload: Parameters<typeof contentApi.create>[0] = {
      type: newType.value,
      title: newTitle.value.trim(),
      description: newDescription.value.trim() || null,
    }
    if (newType.value === 'link') {
      payload.file_url = newLinkUrl.value.trim()
    } else if (newType.value === 'text') {
      payload.content_data = { plain: newTextBody.value }
    }
    const created = await contentApi.create(payload)
    emit('picked', created)
  } catch (e) {
    error.value = extractErrorMessage(e, 'Yaratishda xato')
  } finally {
    submitting.value = false
  }
}

function fmtDate(s: string): string {
  return s.slice(0, 10)
}
</script>

<template>
  <UiDrawer :open="open" :title="t('content_picker.title')" width="lg" @close="emit('close')">
    <p class="text-[13px] text-muted-foreground mb-4">{{ t('content_picker.subtitle') }}</p>

    <!-- Tabs -->
    <div class="border-b border-border mb-4 flex gap-1">
      <button
        type="button"
        class="px-3 py-2 text-[13px] font-medium border-b-2 -mb-px transition-colors"
        :class="
          tab === 'existing'
            ? 'border-foreground text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        "
        @click="tab = 'existing'"
      >
        {{ t('content_picker.tab_existing') }}
      </button>
      <button
        type="button"
        class="px-3 py-2 text-[13px] font-medium border-b-2 -mb-px transition-colors"
        :class="
          tab === 'create'
            ? 'border-foreground text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        "
        @click="tab = 'create'"
      >
        {{ t('content_picker.tab_create') }}
      </button>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <!-- Existing tab -->
    <div v-if="tab === 'existing'">
      <div class="grid grid-cols-3 gap-2 mb-4">
        <input
          v-model="searchQ"
          :placeholder="t('content_picker.search')"
          class="rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        />
        <UiSelect v-model="typeFilter" :options="typeOptions" />
        <UiSelect v-model="statusFilter" :options="statusOptions" />
      </div>

      <div v-if="loading && items.length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="items.length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('content_picker.no_content') }}
      </div>
      <div v-else class="space-y-2">
        <button
          v-for="c in items"
          :key="c.id"
          type="button"
          class="w-full text-left p-3 border border-border rounded-md hover:border-foreground hover:bg-muted/40 transition-colors"
          @click="pick(c)"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <UiBadge variant="default">
                  {{ t(`content_picker.type_${c.type}`) }}
                </UiBadge>
                <UiBadge :variant="c.status === 'published' ? 'success' : 'default'">
                  {{ c.status }}
                </UiBadge>
                <span class="font-mono text-[10px] text-muted-foreground">
                  v{{ c.version }} · {{ fmtDate(c.updated_at) }}
                </span>
              </div>
              <div class="text-[14px] font-medium text-foreground truncate">{{ c.title }}</div>
              <div
                v-if="c.description"
                class="text-[12px] text-muted-foreground line-clamp-1 mt-0.5"
              >
                {{ c.description }}
              </div>
            </div>
            <span class="text-[12px] text-muted-foreground shrink-0">
              {{ t('content_picker.select') }} →
            </span>
          </div>
        </button>
      </div>
    </div>

    <!-- Create tab -->
    <form v-else id="content-create-form" @submit.prevent="createAndAttach">
      <UiFormField :label="t('content_picker.field_type')" required>
        <UiSelect v-model="newType" :options="newTypeOptions" />
      </UiFormField>

      <UiFormField :label="t('content_picker.field_title')" required>
        <UiInput v-model="newTitle" required />
      </UiFormField>

      <UiFormField :label="t('content_picker.field_description')">
        <textarea
          v-model="newDescription"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField v-if="newType === 'link'" :label="t('content_picker.field_link_url')" required>
        <UiInput v-model="newLinkUrl" type="url" required placeholder="https://..." />
      </UiFormField>

      <UiFormField v-if="newType === 'text'" :label="t('content_picker.field_text_body')">
        <textarea
          v-model="newTextBody"
          rows="6"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 font-mono outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <p
        v-if="['pdf', 'video', 'file'].includes(newType)"
        class="text-[12px] text-muted-foreground italic"
      >
        Yaratilgandan keyin, kontentni tahrirlash sahifasidan fayl yuklash mumkin.
      </p>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton
          v-if="tab === 'create'"
          type="submit"
          form="content-create-form"
          :loading="submitting"
        >
          {{ t('content_picker.create_and_attach') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
