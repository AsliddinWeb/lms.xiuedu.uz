<script setup lang="ts">
/**
 * Lesson comments panel — Phase 11c.
 *
 * Dars sahifasi yon panelida joylashtiriladi:
 *   <LessonCommentsPanel :lesson-id="..." />
 *
 * Yangi izoh yozish, javob berish (1 daraja), like toggle, tahrir va o'chirish.
 * Top-level izohlar yuqorida, ostida o'sha izohga javoblar — flat-ish nested.
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import {
  commentsApi,
  type LessonCommentPublic,
} from '@shared/api/comments'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import { formatDateTime } from '@shared/utils/datetime'

const props = defineProps<{ lessonId: number }>()
const { t, locale } = useI18n()
const auth = useAuthStore()

const comments = ref<LessonCommentPublic[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref<string | null>(null)

const composer = ref('')
const sending = ref(false)

const replyingTo = ref<number | null>(null)
const replyBody = ref('')

const editingId = ref<number | null>(null)
const editBody = ref('')

// Top-level va child uchun ajratish
const topLevel = computed(() =>
  comments.value.filter((c) => !c.parent_comment_id),
)

function children(parentId: number): LessonCommentPublic[] {
  return comments.value.filter((c) => c.parent_comment_id === parentId)
}

function canModify(c: LessonCommentPublic): boolean {
  // Faqat muallif tahrirlay oladi, o'chirishni — muallif yoki o'qituvchi
  return c.author_id === auth.user?.id
}

function canDelete(c: LessonCommentPublic): boolean {
  return c.author_id === auth.user?.id || auth.hasPermission('course.create')
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await commentsApi.list(props.lessonId, { page_size: 100 })
    comments.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function submitTop() {
  const body = composer.value.trim()
  if (!body) return
  sending.value = true
  try {
    const c = await commentsApi.create(props.lessonId, { body })
    comments.value = [...comments.value, c]
    total.value += 1
    composer.value = ''
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    sending.value = false
  }
}

async function submitReply(parentId: number) {
  const body = replyBody.value.trim()
  if (!body) return
  sending.value = true
  try {
    const c = await commentsApi.create(props.lessonId, {
      body,
      parent_comment_id: parentId,
    })
    comments.value = [...comments.value, c]
    total.value += 1
    replyBody.value = ''
    replyingTo.value = null
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    sending.value = false
  }
}

async function saveEdit(commentId: number) {
  const body = editBody.value.trim()
  if (!body) return
  sending.value = true
  try {
    const updated = await commentsApi.edit(commentId, body)
    const idx = comments.value.findIndex((c) => c.id === commentId)
    if (idx >= 0) comments.value.splice(idx, 1, updated)
    editingId.value = null
    editBody.value = ''
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    sending.value = false
  }
}

async function remove(commentId: number) {
  if (!window.confirm(t('comments.delete_confirm'))) return
  try {
    await commentsApi.remove(commentId)
    const idx = comments.value.findIndex((c) => c.id === commentId)
    if (idx >= 0) comments.value.splice(idx, 1)
    total.value = Math.max(0, total.value - 1)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

async function toggleLike(c: LessonCommentPublic) {
  try {
    const updated = await commentsApi.toggleLike(c.id)
    const idx = comments.value.findIndex((x) => x.id === c.id)
    if (idx >= 0) comments.value.splice(idx, 1, updated)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

function startReply(parentId: number) {
  replyingTo.value = parentId
  replyBody.value = ''
}

function startEdit(c: LessonCommentPublic) {
  editingId.value = c.id
  editBody.value = c.body
}

function authorLabel(c: LessonCommentPublic): string {
  if (c.author_name) return c.author_name
  if (c.author_id === null) return t('comments.anonymous', { id: 0 })
  return t('comments.anonymous', { id: c.author_id })
}

function fmtDateTime(iso: string): string {
  return formatDateTime(iso, locale.value)
}

onMounted(load)
watch(
  () => props.lessonId,
  () => {
    void load()
  },
)
</script>

<template>
  <section class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-[15px] font-semibold">
        {{ t('comments.title') }}
      </h3>
      <span class="text-[12px] font-mono text-muted-foreground">
        {{ t('comments.count_label', { n: total }) }}
      </span>
    </div>

    <UiAlert v-if="error" variant="danger">{{ error }}</UiAlert>

    <!-- Top-level composer -->
    <UiCard class="p-3">
      <textarea
        v-model="composer"
        rows="2"
        class="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
        :placeholder="t('comments.placeholder')"
        :disabled="sending"
      ></textarea>
      <div class="flex justify-end mt-2">
        <UiButton
          size="sm"
          :disabled="sending || !composer.trim()"
          @click="submitTop"
        >
          {{ t('comments.send') }}
        </UiButton>
      </div>
    </UiCard>

    <!-- Comments list -->
    <div v-if="loading">
      <UiSkeleton :count="4" />
    </div>

    <div
      v-else-if="topLevel.length === 0"
      class="text-center text-[13px] text-muted-foreground py-8"
    >
      {{ t('comments.empty') }}
    </div>

    <ul v-else class="space-y-2">
      <li v-for="c in topLevel" :key="c.id">
        <UiCard class="p-3">
          <!-- Author + actions -->
          <div class="flex items-start justify-between gap-3 mb-1">
            <span class="text-[12px] font-mono text-muted-foreground">
              {{ authorLabel(c) }} · {{ fmtDateTime(c.created_at) }}
              <span v-if="c.edited_at"> · {{ t('comments.edited') }}</span>
            </span>
            <div class="flex items-center gap-2 text-[12px] font-mono">
              <button
                type="button"
                :class="c.liked_by_me ? 'text-foreground' : 'text-muted-foreground'"
                :aria-label="c.liked_by_me ? t('comments.unlike') ?? 'unlike' : t('comments.like') ?? 'like'"
                :aria-pressed="c.liked_by_me"
                @click="toggleLike(c)"
              >
                ♥ {{ c.like_count }}
              </button>
              <button
                v-if="canModify(c)"
                type="button"
                class="text-muted-foreground hover:text-foreground"
                @click="startEdit(c)"
              >
                {{ t('comments.edit') }}
              </button>
              <button
                v-if="canDelete(c)"
                type="button"
                class="text-muted-foreground hover:text-foreground"
                @click="remove(c.id)"
              >
                {{ t('comments.delete') }}
              </button>
            </div>
          </div>

          <!-- Body (edit yoki ko'rsatish) -->
          <div v-if="editingId === c.id">
            <textarea
              v-model="editBody"
              rows="2"
              class="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
            ></textarea>
            <div class="flex justify-end gap-2 mt-2">
              <UiButton
                variant="outline"
                size="sm"
                @click="editingId = null"
              >
                {{ t('comments.cancel') }}
              </UiButton>
              <UiButton
                size="sm"
                :disabled="sending || !editBody.trim()"
                @click="saveEdit(c.id)"
              >
                {{ t('comments.save') }}
              </UiButton>
            </div>
          </div>
          <div v-else class="text-[13px] whitespace-pre-wrap break-words">
            {{ c.body }}
          </div>

          <!-- Reply tugmasi -->
          <div class="mt-2">
            <button
              type="button"
              class="text-[12px] font-mono text-muted-foreground hover:text-foreground"
              @click="startReply(c.id)"
            >
              {{ t('comments.reply') }}
            </button>
          </div>

          <!-- Reply composer -->
          <div
            v-if="replyingTo === c.id"
            class="mt-2 pl-4 border-l-2 border-border"
          >
            <textarea
              v-model="replyBody"
              rows="2"
              class="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
              :placeholder="t('comments.reply_placeholder')"
            ></textarea>
            <div class="flex justify-end gap-2 mt-2">
              <UiButton
                variant="outline"
                size="sm"
                @click="replyingTo = null"
              >
                {{ t('comments.cancel_reply') }}
              </UiButton>
              <UiButton
                size="sm"
                :disabled="sending || !replyBody.trim()"
                @click="submitReply(c.id)"
              >
                {{ t('comments.send') }}
              </UiButton>
            </div>
          </div>

          <!-- Children (1 daraja) -->
          <ul
            v-if="children(c.id).length > 0"
            class="mt-3 space-y-2 pl-4 border-l-2 border-border"
          >
            <li v-for="ch in children(c.id)" :key="ch.id">
              <div class="flex items-start justify-between gap-3 mb-1">
                <span class="text-[11px] font-mono text-muted-foreground">
                  {{ authorLabel(ch) }} · {{ fmtDateTime(ch.created_at) }}
                  <span v-if="ch.edited_at"> · {{ t('comments.edited') }}</span>
                </span>
                <div class="flex items-center gap-2 text-[11px] font-mono">
                  <button
                    type="button"
                    :class="ch.liked_by_me ? 'text-foreground' : 'text-muted-foreground'"
                    @click="toggleLike(ch)"
                  >
                    ♥ {{ ch.like_count }}
                  </button>
                  <button
                    v-if="canModify(ch)"
                    type="button"
                    class="text-muted-foreground hover:text-foreground"
                    @click="startEdit(ch)"
                  >
                    {{ t('comments.edit') }}
                  </button>
                  <button
                    v-if="canDelete(ch)"
                    type="button"
                    class="text-muted-foreground hover:text-foreground"
                    @click="remove(ch.id)"
                  >
                    {{ t('comments.delete') }}
                  </button>
                </div>
              </div>
              <div v-if="editingId === ch.id">
                <textarea
                  v-model="editBody"
                  rows="2"
                  class="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
                ></textarea>
                <div class="flex justify-end gap-2 mt-2">
                  <UiButton
                    variant="outline"
                    size="sm"
                    @click="editingId = null"
                  >
                    {{ t('comments.cancel') }}
                  </UiButton>
                  <UiButton
                    size="sm"
                    :disabled="sending || !editBody.trim()"
                    @click="saveEdit(ch.id)"
                  >
                    {{ t('comments.save') }}
                  </UiButton>
                </div>
              </div>
              <div v-else class="text-[12px] whitespace-pre-wrap break-words">
                {{ ch.body }}
              </div>
            </li>
          </ul>
        </UiCard>
      </li>
    </ul>
  </section>
</template>
