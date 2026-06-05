<script setup lang="ts">
/**
 * Chat sahifasi — Phase 11b.
 *
 * Tuzilma:
 *   ┌─────────────┬─────────────────────────┐
 *   │ Sidebar     │ Header (peer/title)     │
 *   │ — suhbatlar │─────────────────────────│
 *   │   ro'yxati  │ Xabarlar oqimi          │
 *   │ — qidiruv   │                         │
 *   │ — yangi chat│                         │
 *   │             │─────────────────────────│
 *   │             │ Composer (input + send) │
 *   └─────────────┴─────────────────────────┘
 *
 * WebSocket orqali kelgan `message.new` / `message.edit` / `message.delete`
 * eventlari local state'ga merge qilinadi. Boshqa suhbatga kelsa,
 * sidebar'dagi unread count yangilanadi.
 */

import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import {
  chatApi,
  type ChatContact,
  type ConversationPublic,
  type MessagePublic,
} from '@shared/api/chat'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import { useChatSocket } from '@user/composables/useChatSocket'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const conversations = ref<ConversationPublic[]>([])
const activeId = ref<number | null>(null)
const messages = ref<MessagePublic[]>([])
const hasMore = ref(false)
const search = ref('')
const composer = ref('')
const loadingList = ref(true)
const loadingThread = ref(false)
const error = ref<string | null>(null)
const sending = ref(false)
const thread = ref<HTMLDivElement | null>(null)

const ws = useChatSocket()

// Phase 26 — yangi suhbat (kontakt picker)
const showContacts = ref(false)
const contacts = ref<ChatContact[]>([])
const loadingContacts = ref(false)

async function openContacts() {
  showContacts.value = true
  if (contacts.value.length === 0) {
    loadingContacts.value = true
    try {
      contacts.value = await chatApi.contacts()
    } catch {
      contacts.value = []
    } finally {
      loadingContacts.value = false
    }
  }
}

async function startChat(c: ChatContact) {
  showContacts.value = false
  try {
    const conv = await chatApi.openDirect(c.user_id)
    await loadConversations()
    await openConversation(conv.id)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

const activeConv = computed<ConversationPublic | null>(
  () => conversations.value.find((c) => c.id === activeId.value) ?? null,
)

const filtered = computed<ConversationPublic[]>(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return conversations.value
  return conversations.value.filter((c) => {
    const t1 = (c.title ?? '').toLowerCase()
    const t2 = (c.last_message_preview ?? '').toLowerCase()
    return t1.includes(q) || t2.includes(q)
  })
})

function convLabel(c: ConversationPublic): string {
  if (c.title) return c.title
  if (c.type === 'direct') {
    const peer = c.member_ids.find((id) => id !== auth.user?.id)
    if (peer) return c.member_names?.[peer] ?? `user#${peer}`
    return t('chat.type_direct')
  }
  return t(`chat.type_${c.type}`)
}

function fmtTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function loadConversations() {
  loadingList.value = true
  error.value = null
  try {
    const data = await chatApi.listConversations({ page_size: 100 })
    conversations.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loadingList.value = false
  }
}

async function openConversation(id: number) {
  if (activeId.value === id) return
  activeId.value = id
  await router.replace({ name: 'chat', query: { c: String(id) } })
  await loadMessages()
  // Local unread'ni nolga tushiramiz (server ham mark_read qiladi)
  const c = conversations.value.find((x) => x.id === id)
  if (c) c.unread_count = 0
  try {
    await chatApi.markRead(id)
  } catch {
    // ignore
  }
}

async function loadMessages() {
  if (activeId.value === null) return
  loadingThread.value = true
  try {
    const data = await chatApi.listMessages(activeId.value, { limit: 50 })
    messages.value = data.items
    hasMore.value = data.has_more
    await nextTick()
    scrollToBottom()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loadingThread.value = false
  }
}

async function loadOlder() {
  if (activeId.value === null || !messages.value.length) return
  const oldestId = messages.value[0].id
  const prevHeight = thread.value?.scrollHeight ?? 0
  try {
    const data = await chatApi.listMessages(activeId.value, {
      before_id: oldestId,
      limit: 50,
    })
    messages.value = [...data.items, ...messages.value]
    hasMore.value = data.has_more
    await nextTick()
    if (thread.value) {
      thread.value.scrollTop = thread.value.scrollHeight - prevHeight
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

function scrollToBottom() {
  if (thread.value) {
    thread.value.scrollTop = thread.value.scrollHeight
  }
}

async function send() {
  const body = composer.value.trim()
  if (!body || activeId.value === null) return
  sending.value = true
  try {
    const msg = await chatApi.sendMessage(activeId.value, { body })
    // WebSocket ham yetkazadi — duplicat oldini olamiz
    if (!messages.value.some((m) => m.id === msg.id)) {
      messages.value.push(msg)
      await nextTick()
      scrollToBottom()
    }
    composer.value = ''
    // Sidebar last_message_preview yangilash
    const c = conversations.value.find((x) => x.id === activeId.value)
    if (c) {
      c.last_message_preview = body
      c.last_message_at = msg.created_at
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    sending.value = false
  }
}

function applyWsEvent(ev: { type: string; conversation_id: number; payload: Record<string, unknown> }) {
  if (ev.type === 'message.new') {
    const msg = ev.payload as unknown as MessagePublic
    if (msg.conversation_id === activeId.value) {
      if (!messages.value.some((m) => m.id === msg.id)) {
        messages.value.push(msg)
        nextTick(scrollToBottom)
      }
    } else {
      const c = conversations.value.find((x) => x.id === msg.conversation_id)
      if (c) {
        c.unread_count += 1
        c.last_message_preview = msg.body ?? null
        c.last_message_at = msg.created_at
      }
    }
  } else if (ev.type === 'message.edit') {
    const msg = ev.payload as unknown as MessagePublic
    if (msg.conversation_id === activeId.value) {
      const idx = messages.value.findIndex((m) => m.id === msg.id)
      if (idx >= 0) messages.value.splice(idx, 1, msg)
    }
  } else if (ev.type === 'message.delete') {
    const id = (ev.payload as { id: number }).id
    if (ev.conversation_id === activeId.value) {
      const idx = messages.value.findIndex((m) => m.id === id)
      if (idx >= 0) {
        const cur = messages.value[idx]
        messages.value.splice(idx, 1, { ...cur, deleted_at: new Date().toISOString(), body: null })
      }
    }
  }
}

onMounted(async () => {
  await loadConversations()
  // ?c=<id> bilan ochilgan bo'lsa, o'sha suhbatni ochamiz
  const q = route.query.c
  if (typeof q === 'string') {
    const id = Number(q)
    if (Number.isFinite(id)) await openConversation(id)
  }
  ws.connect()
  ws.on(applyWsEvent)
})

watch(
  () => route.query.c,
  (v) => {
    if (typeof v === 'string') {
      const id = Number(v)
      if (Number.isFinite(id) && id !== activeId.value) openConversation(id)
    }
  },
)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('chat.title')]"
    class="mb-4"
  />

  <div class="mb-4 flex items-end justify-between gap-4 flex-wrap">
    <div>
      <h1 class="page-title mb-1.5">{{ t('chat.title') }}</h1>
      <p class="page-subtitle">{{ t('chat.subtitle') }}</p>
    </div>
    <div class="flex items-center gap-2 text-[12px] font-mono text-muted-foreground">
      <span
        :class="ws.connected.value ? 'text-foreground' : 'text-muted-foreground'"
      >
        ● {{ ws.connected.value ? t('chat.ws_connected') : t('chat.ws_disconnected') }}
      </span>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- Phase 13.27 — mobile: sidebar/thread toggle, desktop: side-by-side -->
  <div
    class="grid grid-cols-1 md:grid-cols-[280px_1fr] lg:grid-cols-[320px_1fr] gap-0 border border-border rounded-md overflow-hidden bg-background"
    style="height: calc(100vh - 220px); min-height: 480px;"
  >
    <!-- Sidebar (mobile: aktiv suhbat tanlangan bo'lsa yashirin) -->
    <aside
      class="border-r border-border flex flex-col"
      :class="{ 'hidden md:flex': activeId !== null }"
    >
      <div class="px-3 py-2 border-b border-border space-y-2">
        <div class="flex items-center gap-2">
          <UiInput
            v-model="search"
            :placeholder="t('chat.search_placeholder')"
            class="flex-1"
          />
          <UiButton size="sm" @click="openContacts">+ {{ t('chat.new') }}</UiButton>
        </div>

        <!-- Kontakt picker (Phase 26) -->
        <div v-if="showContacts" class="border border-border rounded-md bg-card">
          <div class="px-3 py-2 border-b border-border flex items-center justify-between">
            <span class="text-[12px] font-semibold">{{ t('chat.new_title') }}</span>
            <button
              type="button"
              class="text-muted-foreground hover:text-foreground"
              @click="showContacts = false"
            >
              ✕
            </button>
          </div>
          <div v-if="loadingContacts" class="p-3">
            <UiSkeleton :count="3" />
          </div>
          <div
            v-else-if="contacts.length === 0"
            class="p-4 text-center text-[12px] text-muted-foreground"
          >
            {{ t('chat.no_contacts') }}
          </div>
          <ul v-else class="max-h-[260px] overflow-y-auto divide-y divide-border">
            <li v-for="ct in contacts" :key="ct.user_id">
              <button
                type="button"
                class="w-full text-left px-3 py-2 hover:bg-muted/40 transition-colors flex items-center gap-2.5"
                @click="startChat(ct)"
              >
                <div class="w-7 h-7 rounded-full bg-muted grid place-items-center text-[11px] font-semibold shrink-0">
                  {{ ct.full_name.slice(0, 1) }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-[13px] font-medium truncate">{{ ct.full_name }}</div>
                  <div class="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                    {{ t(`chat.relation_${ct.relation}`) }}
                  </div>
                </div>
              </button>
            </li>
          </ul>
        </div>
      </div>

      <div v-if="loadingList" class="p-3">
        <UiSkeleton :count="4" />
      </div>

      <div
        v-else-if="filtered.length === 0"
        class="flex-1 flex items-center justify-center text-[13px] text-muted-foreground p-4 text-center"
      >
        {{ t('chat.empty_list') }}
      </div>

      <ul v-else class="flex-1 overflow-y-auto divide-y divide-border">
        <li v-for="c in filtered" :key="c.id">
          <button
            type="button"
            class="block w-full text-left px-3 py-2.5 hover:bg-muted/40 transition-colors"
            :class="{ 'bg-muted/60': c.id === activeId }"
            @click="openConversation(c.id)"
          >
            <div class="flex items-center justify-between gap-2 mb-0.5">
              <span class="text-[13px] font-medium truncate">
                {{ convLabel(c) }}
              </span>
              <span
                v-if="c.last_message_at"
                class="text-[11px] font-mono text-muted-foreground shrink-0"
              >
                {{ fmtTime(c.last_message_at) }}
              </span>
            </div>
            <div class="flex items-center justify-between gap-2">
              <span class="text-[12px] text-muted-foreground truncate flex-1">
                {{ c.last_message_preview || '—' }}
              </span>
              <span
                v-if="c.unread_count > 0"
                class="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-foreground text-background shrink-0"
              >
                {{ c.unread_count }}
              </span>
            </div>
          </button>
        </li>
      </ul>
    </aside>

    <!-- Thread + composer (mobile: aktiv suhbat yo'q bo'lsa yashirin) -->
    <section
      class="flex flex-col"
      :class="{ 'hidden md:flex': activeId === null }"
    >
      <!-- Header -->
      <header
        v-if="activeConv"
        class="px-4 py-3 border-b border-border flex items-center justify-between gap-3"
      >
        <div class="flex items-center gap-2 min-w-0">
          <!-- Mobile back tugma -->
          <button
            type="button"
            class="md:hidden font-mono text-[11px] text-muted-foreground hover:text-foreground"
            :aria-label="t('chat.back_to_list')"
            @click="activeId = null"
          >
            ←
          </button>
          <div class="min-w-0">
            <div class="text-[12px] font-mono text-muted-foreground uppercase">
              {{ t(`chat.type_${activeConv.type}`) }}
            </div>
            <h2 class="text-[15px] font-semibold truncate">
              {{ convLabel(activeConv) }}
            </h2>
          </div>
        </div>
        <div class="text-[12px] text-muted-foreground hidden sm:block">
          {{ t('chat.members_count', { n: activeConv.member_ids.length }) }}
        </div>
      </header>

      <!-- Empty (no active conversation) -->
      <div
        v-if="!activeConv"
        class="flex-1 flex items-center justify-center text-muted-foreground text-[13px] p-6 text-center"
      >
        {{ t('chat.select_conversation') }}
      </div>

      <!-- Messages -->
      <div
        v-else
        ref="thread"
        class="flex-1 overflow-y-auto bg-muted/10 px-4 py-3"
      >
        <div v-if="loadingThread" class="py-4">
          <UiSkeleton :count="5" />
        </div>

        <div v-else>
          <div v-if="hasMore" class="text-center mb-3">
            <button
              type="button"
              class="text-[12px] font-mono text-muted-foreground underline underline-offset-2"
              @click="loadOlder"
            >
              {{ t('chat.load_older') }}
            </button>
          </div>

          <div
            v-if="messages.length === 0"
            class="text-center text-[13px] text-muted-foreground py-10"
          >
            {{ t('chat.empty_thread') }}
          </div>

          <ul v-else class="space-y-1.5">
            <li
              v-for="m in messages"
              :key="m.id"
              :class="m.sender_id === auth.user?.id ? 'flex justify-end' : 'flex justify-start'"
            >
              <div
                class="max-w-[70%] rounded-md px-3 py-2"
                :class="
                  m.sender_id === auth.user?.id
                    ? 'bg-foreground text-background'
                    : 'bg-background border border-border'
                "
              >
                <div
                  v-if="
                    activeConv && activeConv.type !== 'direct' &&
                    m.sender_id !== auth.user?.id && m.sender_name
                  "
                  class="text-[11px] font-mono opacity-70 mb-0.5"
                >
                  {{ m.sender_name }}
                </div>
                <div
                  v-if="m.deleted_at"
                  class="text-[12px] italic opacity-70"
                >
                  {{ t('chat.deleted') }}
                </div>
                <div v-else class="text-[13px] whitespace-pre-wrap break-words">
                  {{ m.body }}
                </div>
                <div
                  class="text-[10px] font-mono opacity-60 mt-1 flex items-center gap-1"
                >
                  <span>{{ fmtTime(m.created_at) }}</span>
                  <span v-if="m.edited_at">· {{ t('chat.edited') }}</span>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Composer -->
      <div
        v-if="activeConv"
        class="border-t border-border p-3 flex items-end gap-2 bg-background"
      >
        <textarea
          v-model="composer"
          rows="2"
          class="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
          :placeholder="t('chat.composer_placeholder')"
          :disabled="sending"
          @keydown.enter.exact.prevent="send"
        ></textarea>
        <UiButton :disabled="sending || !composer.trim()" @click="send">
          {{ t('chat.send') }}
        </UiButton>
      </div>
    </section>
  </div>
</template>
