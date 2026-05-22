<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { rubricsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type { Rubric } from '@shared/types/assignments'

import RubricDrawer from '@user/components/rubrics/RubricDrawer.vue'

const { t } = useI18n()

const items = ref<Rubric[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQ = ref('')

const drawerOpen = ref(false)
const editing = ref<Rubric | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await rubricsApi.list({
      q: searchQ.value || undefined,
      page_size: 100,
    })
    items.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQ, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})

function openCreate() {
  editing.value = null
  drawerOpen.value = true
}

function openEdit(r: Rubric) {
  editing.value = r
  drawerOpen.value = true
}

async function handleDelete(r: Rubric) {
  const ok = await confirm({
    title: t('rubrics.delete_confirm'),
    description: r.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await rubricsApi.remove(r.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('rubrics.title')]"
    class="mb-6"
  />
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('rubrics.title') }}</h1>
      <p class="page-subtitle">{{ t('rubrics.subtitle') }}</p>
    </div>
    <UiButton @click="openCreate">+ {{ t('rubrics.new') }}</UiButton>
  </div>

  <div class="flex flex-wrap gap-3 items-center mb-6">
    <div class="flex-1 min-w-[200px] max-w-[320px]">
      <UiInput
        v-model="searchQ"
        type="search"
        :placeholder="t('common.search')"
      />
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && items.length === 0" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiCard v-else-if="items.length === 0" class="text-center py-12">
    <div class="text-muted-foreground">{{ t('rubrics.no_rubrics') }}</div>
  </UiCard>

  <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
    <UiCard v-for="r in items" :key="r.id">
      <template #header>
        <div class="flex-1 min-w-0">
          <h3 class="text-base font-semibold text-foreground truncate">{{ r.title }}</h3>
          <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
            {{ t('rubrics.total_label', { n: r.total_points }) }} ·
            {{ r.criteria.length }} kriteriya
          </div>
        </div>
      </template>

      <p
        v-if="r.description"
        class="text-[13px] text-muted-foreground line-clamp-2 mb-3"
      >
        {{ r.description }}
      </p>

      <ul class="space-y-1 text-[12px]">
        <li
          v-for="c in r.criteria"
          :key="c.key"
          class="flex items-center justify-between gap-2 text-muted-foreground"
        >
          <span class="truncate">{{ c.name }}</span>
          <span class="font-mono shrink-0">max {{ c.max_points }}</span>
        </li>
      </ul>

      <template #actions>
        <div class="flex gap-1.5">
          <UiButton variant="outline" size="sm" @click="openEdit(r)">
            {{ t('common.edit') }}
          </UiButton>
          <UiButton
            variant="ghost"
            size="sm"
            class="text-danger-600"
            @click="handleDelete(r)"
          >
            {{ t('common.delete') }}
          </UiButton>
        </div>
      </template>
    </UiCard>
  </div>

  <RubricDrawer
    :open="drawerOpen"
    :rubric="editing"
    @close="drawerOpen = false"
    @saved="load"
  />
</template>
