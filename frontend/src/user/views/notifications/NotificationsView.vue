<script setup lang="ts">
/**
 * Phase 7d — Full notifications list page.
 */

import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import {
  notificationsApi,
  type NotificationPublic,
} from '@shared/api/notifications'
import { extractErrorMessage } from '@shared/api/client'

const { t } = useI18n()
const router = useRouter()

const items = ref<NotificationPublic[]>([])
const unreadCount = ref(0)
const total = ref(0)
const loading = ref(true)
const error = ref<string | null>(null)
const unreadOnly = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await notificationsApi.list({
      unread_only: unreadOnly.value,
      page: 1,
      page_size: 100,
    })
    items.value = data.items
    total.value = data.total
    unreadCount.value = data.unread_count
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function handleClick(n: NotificationPublic) {
  if (!n.read_at) {
    try {
      await notificationsApi.markRead(n.id)
      n.read_at = new Date().toISOString()
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // ignore
    }
  }
  if (n.action_url) router.push(n.action_url)
}

async function handleMarkAll() {
  try {
    await notificationsApi.markAllRead()
    const now = new Date().toISOString()
    items.value.forEach((n) => {
      if (!n.read_at) n.read_at = now
    })
    unreadCount.value = 0
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

function eventLabel(type: string): string {
  return t(`notifications.event_${type.replace('.', '_')}`)
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('notifications.title')]"
    class="mb-6"
  />

  <div class="mb-6 flex items-end justify-between gap-4 flex-wrap">
    <div>
      <h1 class="page-title mb-1.5">{{ t('notifications.title') }}</h1>
      <p class="page-subtitle">
        {{ t('notifications.subtitle', { total, unread: unreadCount }) }}
      </p>
    </div>
    <div class="flex items-center gap-2">
      <label class="text-[13px] flex items-center gap-2">
        <input
          v-model="unreadOnly"
          type="checkbox"
          @change="load"
        />
        {{ t('notifications.filter_unread_only') }}
      </label>
      <UiButton v-if="unreadCount > 0" variant="outline" @click="handleMarkAll">
        {{ t('notifications.mark_all_read') }}
      </UiButton>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiCard
    v-else-if="items.length === 0"
    class="py-12 text-center text-muted-foreground"
  >
    {{ t('notifications.empty') }}
  </UiCard>

  <UiCard v-else no-padding>
    <ul class="divide-y divide-border">
      <li v-for="n in items" :key="n.id">
        <button
          type="button"
          class="block w-full text-left px-4 py-3 hover:bg-muted/40 transition-colors"
          :class="{ 'bg-muted/20': !n.read_at }"
          @click="handleClick(n)"
        >
          <div class="flex items-start gap-3">
            <span
              v-if="!n.read_at"
              class="mt-1.5 inline-block w-2 h-2 rounded-full bg-foreground shrink-0"
            ></span>
            <span v-else class="mt-1.5 inline-block w-2 h-2 shrink-0"></span>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <UiBadge variant="default" class="shrink-0">
                  {{ eventLabel(n.event_type) }}
                </UiBadge>
                <span class="text-[11px] font-mono text-muted-foreground">
                  {{ fmtDateTime(n.created_at) }}
                </span>
              </div>
              <div class="text-[14px] font-medium text-foreground">
                {{ n.title }}
              </div>
              <div
                v-if="n.body"
                class="text-[13px] text-muted-foreground mt-0.5"
              >
                {{ n.body }}
              </div>
              <div
                v-if="n.action_url"
                class="text-[11px] font-mono text-muted-foreground mt-1.5"
              >
                → {{ n.action_url }}
              </div>
            </div>
          </div>
        </button>
      </li>
    </ul>
  </UiCard>
</template>
