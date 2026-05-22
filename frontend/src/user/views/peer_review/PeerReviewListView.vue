<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { peerReviewsApi } from '@shared/api/assignments'
import { extractErrorMessage } from '@shared/api/client'
import type { PeerReview } from '@shared/types/assignments'

const { t, locale } = useI18n()
const router = useRouter()

const items = ref<PeerReview[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
type Filter = 'pending' | 'all'
const filter = ref<Filter>('pending')

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await peerReviewsApi.listMine(filter.value === 'pending')
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

function open(pr: PeerReview) {
  router.push({ name: 'peer-review-submit', params: { id: pr.id } })
}

function fmtDate(s: string | null): string {
  if (!s) return '—'
  try {
    return new Intl.DateTimeFormat(locale.value, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('peer_review.title')]"
    class="mb-6"
  />
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('peer_review.title') }}</h1>
      <p class="page-subtitle">{{ t('peer_review.subtitle') }}</p>
    </div>
    <div class="flex items-center gap-1">
      <button
        v-for="opt in (['pending', 'all'] as Filter[])"
        :key="opt"
        type="button"
        class="px-2.5 py-1.5 rounded-md text-[12px] font-medium border transition-colors"
        :class="
          filter === opt
            ? 'bg-foreground text-background border-foreground'
            : 'bg-background text-muted-foreground border-border hover:border-foreground hover:text-foreground'
        "
        @click="filter = opt; load()"
      >
        {{
          opt === 'pending'
            ? t('grading_inbox.filter_pending')
            : t('grading_inbox.filter_all')
        }}
      </button>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && items.length === 0" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiCard v-else-if="items.length === 0" class="text-center py-12">
    <div class="text-muted-foreground">{{ t('peer_review.no_pending') }}</div>
  </UiCard>

  <UiCard v-else no-padding>
    <table class="w-full text-[13px]">
      <thead class="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
        <tr>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">#</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_status') }}</th>
          <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('grading_inbox.col_submitted') }}</th>
          <th scope="col" class="px-4 py-2.5"></th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="pr in items" :key="pr.id" class="hover:bg-muted/30">
          <td class="px-4 py-3 font-mono">#{{ pr.id }}</td>
          <td class="px-4 py-3">
            <UiBadge
              :variant="pr.submitted_at ? 'success' : 'default'"
              with-dot
            >
              {{
                pr.submitted_at
                  ? t('assignments.status_graded')
                  : t('grading_inbox.filter_pending')
              }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">
            {{ fmtDate(pr.submitted_at) }}
          </td>
          <td class="px-4 py-3 text-right">
            <UiButton
              variant="outline"
              size="sm"
              :disabled="pr.submitted_at !== null"
              @click="open(pr)"
            >
              {{ t('grading_inbox.review') }}
            </UiButton>
          </td>
        </tr>
      </tbody>
    </table>
  </UiCard>
</template>
