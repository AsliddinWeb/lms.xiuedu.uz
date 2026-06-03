<script setup lang="ts">
/**
 * Forum mavzu detali — Phase 11b.
 *
 * Mavzu sarlavhasi va birinchi xabar + postlar ro'yxati. Javob yozish form'i.
 * Lock/pin tugmalari faqat o'qituvchida ko'rinadi.
 */

import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import {
  forumApi,
  type ForumPostPublic,
  type ForumThreadPublic,
} from '@shared/api/forum'
import { coursesApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const threadId = computed(() => Number(route.params.threadId))

const thread = ref<ForumThreadPublic | null>(null)
const posts = ref<ForumPostPublic[]>([])
const courseTitle = ref('')
const loading = ref(true)
const error = ref<string | null>(null)
const reply = ref('')
const replying = ref(false)

const canModerate = computed(() => auth.hasPermission('course.create'))
const canReply = computed(() => {
  if (!thread.value) return false
  if (thread.value.is_locked) return false
  if (thread.value.is_announcement && !canModerate.value) return false
  return true
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const [th, postsData] = await Promise.all([
      forumApi.getThread(threadId.value),
      forumApi.listPosts(threadId.value, { page_size: 100 }),
    ])
    thread.value = th
    posts.value = postsData.items
    if (th.course_id) {
      coursesApi
        .get(th.course_id)
        .then((c) => (courseTitle.value = c.title))
        .catch(() => undefined)
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function postReply() {
  const body = reply.value.trim()
  if (!body) return
  replying.value = true
  try {
    const p = await forumApi.createPost(threadId.value, { body })
    posts.value.push(p)
    if (thread.value) {
      thread.value.post_count += 1
      thread.value.last_reply_at = p.created_at
    }
    reply.value = ''
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    replying.value = false
  }
}

async function toggleLike(post: ForumPostPublic) {
  try {
    const updated = await forumApi.toggleLike(post.id)
    const idx = posts.value.findIndex((p) => p.id === post.id)
    if (idx >= 0) posts.value.splice(idx, 1, updated)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

async function deletePost(post: ForumPostPublic) {
  if (!window.confirm(t('forum.post_delete_confirm'))) return
  try {
    await forumApi.deletePost(post.id)
    const idx = posts.value.findIndex((p) => p.id === post.id)
    if (idx >= 0) posts.value.splice(idx, 1)
    if (thread.value) {
      thread.value.post_count = Math.max(0, thread.value.post_count - 1)
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

async function togglePin() {
  if (!thread.value) return
  try {
    thread.value = await forumApi.updateThread(thread.value.id, {
      is_pinned: !thread.value.is_pinned,
    })
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

async function toggleLock() {
  if (!thread.value) return
  try {
    thread.value = await forumApi.updateThread(thread.value.id, {
      is_locked: !thread.value.is_locked,
    })
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

function backToCourse() {
  if (thread.value) {
    router.push({
      name: 'forum-course',
      params: { courseId: thread.value.course_id },
    })
  }
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('forum.title')]"
    class="mb-4"
  />

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading">
    <UiSkeleton :count="6" />
  </div>

  <div v-else-if="thread">
    <!-- Header -->
    <div class="mb-4 flex items-start justify-between gap-4 flex-wrap">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 mb-2 flex-wrap">
          <UiBadge v-if="thread.is_pinned" variant="info">
            {{ t('forum.pinned') }}
          </UiBadge>
          <UiBadge v-if="thread.is_announcement" variant="warning">
            {{ t('forum.announcement') }}
          </UiBadge>
          <UiBadge v-if="thread.is_locked" variant="danger">
            {{ t('forum.locked') }}
          </UiBadge>
        </div>
        <h1 class="page-title mb-1.5">{{ thread.title }}</h1>
        <p class="page-subtitle">
          {{ courseTitle || t('forum.title') }} ·
          {{ t('forum.posts_count', { n: thread.post_count }) }}
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <UiButton variant="outline" size="sm" @click="backToCourse">
          ← {{ t('forum.course_threads') }}
        </UiButton>
        <UiButton
          v-if="canModerate"
          variant="outline"
          size="sm"
          @click="togglePin"
        >
          {{ thread.is_pinned ? t('forum.unpin') : t('forum.pin') }}
        </UiButton>
        <UiButton
          v-if="canModerate"
          variant="outline"
          size="sm"
          @click="toggleLock"
        >
          {{ thread.is_locked ? t('forum.unlock') : t('forum.lock') }}
        </UiButton>
      </div>
    </div>

    <!-- First post (thread.body) -->
    <UiCard v-if="thread.body" class="mb-4 p-4">
      <div class="text-[13px] whitespace-pre-wrap break-words mb-2">
        {{ thread.body }}
      </div>
      <div class="text-[11px] font-mono text-muted-foreground">
        {{ thread.author_name ?? (thread.author_id ? `user#${thread.author_id}` : '—') }}
        · {{ fmtDateTime(thread.created_at) }}
      </div>
    </UiCard>

    <!-- Posts -->
    <ul v-if="posts.length > 0" class="space-y-2 mb-6">
      <li v-for="p in posts" :key="p.id">
        <UiCard class="p-4">
          <div class="flex items-start justify-between gap-3 mb-1">
            <span class="text-[12px] font-mono text-muted-foreground">
              {{ p.author_name ?? (p.author_id ? `user#${p.author_id}` : '—') }}
              · {{ fmtDateTime(p.created_at) }}
              <span v-if="p.edited_at">· {{ t('forum.edited') }}</span>
            </span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="text-[12px] font-mono"
                :class="p.liked_by_me ? 'text-foreground' : 'text-muted-foreground'"
                @click="toggleLike(p)"
              >
                ♥ {{ p.like_count }}
              </button>
              <button
                v-if="p.author_id === auth.user?.id || canModerate"
                type="button"
                class="text-[12px] font-mono text-muted-foreground hover:text-foreground"
                @click="deletePost(p)"
              >
                {{ t('forum.post_delete') }}
              </button>
            </div>
          </div>
          <div class="text-[13px] whitespace-pre-wrap break-words">
            {{ p.body }}
          </div>
        </UiCard>
      </li>
    </ul>

    <!-- Reply composer -->
    <UiCard v-if="canReply" class="p-3">
      <textarea
        v-model="reply"
        rows="3"
        class="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
        :placeholder="t('forum.post_placeholder')"
        :disabled="replying"
      ></textarea>
      <div class="flex justify-end mt-2">
        <UiButton :disabled="replying || !reply.trim()" @click="postReply">
          {{ t('forum.post_reply') }}
        </UiButton>
      </div>
    </UiCard>

    <UiAlert v-else-if="thread.is_locked" variant="warning">
      {{ t('forum.thread_locked_hint') }}
    </UiAlert>
    <UiAlert v-else-if="thread.is_announcement" variant="info">
      {{ t('forum.announcement_hint') }}
    </UiAlert>
  </div>
</template>
