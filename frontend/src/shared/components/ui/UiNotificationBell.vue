<script setup lang="ts">
/**
 * Phase 7d — Notification bell (topbar).
 *
 * Headless Popover pattern (Menu API'sini ishlatamiz, MenuItem'siz panel).
 * - Bell icon + unread badge (raqam, agar >0)
 * - Ochilganda: oxirgi 5 ta bildirishnoma + "Hammasini o'qildi" + "Hammasini ko'rish"
 * - Item bosilganda → action_url ga navigate + o'qildi belgilash
 * - Polling: har 30s da unread count yangilanadi
 */

import { Menu, MenuButton, MenuItems } from '@headlessui/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import {
  notificationsApi,
  type NotificationPublic,
} from '@shared/api/notifications'

const { t } = useI18n()
const router = useRouter()

const items = ref<NotificationPublic[]>([])
const unreadCount = ref(0)
const loading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function refresh() {
  loading.value = true
  try {
    const data = await notificationsApi.list({ page_size: 5 })
    items.value = data.items
    unreadCount.value = data.unread_count
  } finally {
    loading.value = false
  }
}

async function refreshCount() {
  try {
    unreadCount.value = await notificationsApi.unreadCount()
  } catch {
    // silent
  }
}

async function handleClick(n: NotificationPublic) {
  try {
    if (!n.read_at) {
      await notificationsApi.markRead(n.id)
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      const idx = items.value.findIndex((x) => x.id === n.id)
      if (idx >= 0) items.value[idx].read_at = new Date().toISOString()
    }
  } catch {
    // ignore
  }
  if (n.action_url) {
    router.push(n.action_url)
  }
}

async function handleMarkAll() {
  try {
    const marked = await notificationsApi.markAllRead()
    unreadCount.value = 0
    const now = new Date().toISOString()
    items.value.forEach((n) => {
      if (!n.read_at) n.read_at = now
    })
    void marked
  } catch {
    // ignore
  }
}

function badgeLabel(): string {
  if (unreadCount.value > 99) return '99+'
  return String(unreadCount.value)
}

function fmtRelative(iso: string): string {
  const t0 = new Date(iso).getTime()
  const diff = Date.now() - t0
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('notifications.just_now')
  if (mins < 60) return t('notifications.min_ago', { n: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('notifications.hr_ago', { n: hours })
  const days = Math.floor(hours / 24)
  return t('notifications.day_ago', { n: days })
}

function eventLabel(type: string): string {
  return t(`notifications.event_${type.replace('.', '_')}`)
}

const hasUnread = computed(() => unreadCount.value > 0)

onMounted(() => {
  refresh()
  pollTimer = setInterval(refreshCount, 30_000)
})
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <Menu as="div" class="relative">
    <MenuButton
      class="w-9 h-9 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground relative transition outline-none"
      :title="t('nav.notifications')"
      :aria-label="
        hasUnread
          ? `${t('nav.notifications')} (${badgeLabel()})`
          : t('nav.notifications')
      "
      @click="refresh"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        aria-hidden="true"
      >
        <path d="M3 6a5 5 0 0 1 10 0v4l1 2H2l1-2V6z" />
        <path d="M6 14a2 2 0 0 0 4 0" />
      </svg>
      <span
        v-if="hasUnread"
        class="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 grid place-items-center bg-danger-500 text-white text-[10px] font-mono rounded-full"
      >
        {{ badgeLabel() }}
      </span>
    </MenuButton>

    <transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <MenuItems
        class="absolute right-0 mt-1.5 w-[360px] origin-top-right bg-background border border-border rounded-md shadow-lg z-50 focus:outline-none overflow-hidden"
      >
        <div class="flex items-center justify-between px-3 py-2 border-b border-border">
          <div class="text-[13px] font-semibold">{{ t('notifications.title') }}</div>
          <button
            v-if="hasUnread"
            type="button"
            class="text-[11px] font-mono text-muted-foreground hover:text-foreground"
            @click.stop="handleMarkAll"
          >
            {{ t('notifications.mark_all_read') }}
          </button>
        </div>

        <div v-if="loading && items.length === 0" class="py-8 text-center text-[12px] text-muted-foreground">
          {{ t('common.loading') }}
        </div>

        <div
          v-else-if="items.length === 0"
          class="py-10 text-center text-[12px] text-muted-foreground"
        >
          {{ t('notifications.empty') }}
        </div>

        <ul v-else class="max-h-[400px] overflow-y-auto divide-y divide-border">
          <li v-for="n in items" :key="n.id">
            <button
              type="button"
              class="block w-full text-left px-3 py-2.5 hover:bg-muted/40 transition-colors"
              :class="{ 'bg-muted/20': !n.read_at }"
              @click="handleClick(n)"
            >
              <div class="flex items-start gap-2">
                <span
                  v-if="!n.read_at"
                  class="mt-1.5 inline-block w-1.5 h-1.5 rounded-full bg-foreground shrink-0"
                ></span>
                <span v-else class="mt-1.5 inline-block w-1.5 h-1.5 shrink-0"></span>
                <div class="flex-1 min-w-0">
                  <div class="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                    {{ eventLabel(n.event_type) }}
                  </div>
                  <div class="text-[13px] font-medium text-foreground line-clamp-2">
                    {{ n.title }}
                  </div>
                  <div v-if="n.body" class="text-[12px] text-muted-foreground line-clamp-1 mt-0.5">
                    {{ n.body }}
                  </div>
                  <div class="text-[10px] font-mono text-muted-foreground mt-1">
                    {{ fmtRelative(n.created_at) }}
                  </div>
                </div>
              </div>
            </button>
          </li>
        </ul>

        <div class="px-3 py-2 border-t border-border text-center">
          <button
            type="button"
            class="text-[12px] text-muted-foreground hover:text-foreground"
            @click="router.push('/app/notifications')"
          >
            {{ t('notifications.view_all') }} →
          </button>
        </div>
      </MenuItems>
    </transition>
  </Menu>
</template>
