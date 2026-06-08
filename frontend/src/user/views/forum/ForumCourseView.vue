<script setup lang="ts">
/**
 * Forum kurs sahifasi — Phase 11b.
 *
 * Kurs ichidagi mavzular ro'yxati (pinlangan birinchi, keyin last_reply_at).
 * Yangi mavzu yaratish form'i — agar foydalanuvchi kurs a'zosi bo'lsa.
 */

import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import { forumApi, type ForumThreadPublic } from '@shared/api/forum'
import { coursesApi } from '@shared/api/courses'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import { formatDateTime } from '@shared/utils/datetime'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const courseId = computed(() => Number(route.params.courseId))

const threads = ref<ForumThreadPublic[]>([])
const total = ref(0)
const courseTitle = ref('')
const loading = ref(true)
const error = ref<string | null>(null)

const showCreate = ref(false)
const draft = ref({
  title: '',
  body: '',
  is_announcement: false,
})
const creating = ref(false)

const canAnnounce = computed(() => auth.hasPermission('course.create'))

async function load() {
  loading.value = true
  error.value = null
  try {
    const [data, course] = await Promise.all([
      forumApi.listThreads(courseId.value, { page_size: 50 }),
      coursesApi.get(courseId.value).catch(() => null),
    ])
    threads.value = data.items
    total.value = data.total
    courseTitle.value = course?.title ?? ''
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function createThread() {
  if (!draft.value.title.trim()) return
  creating.value = true
  try {
    const t = await forumApi.createThread({
      course_id: courseId.value,
      title: draft.value.title.trim(),
      body: draft.value.body.trim() || null,
      is_announcement: draft.value.is_announcement && canAnnounce.value,
    })
    threads.value = [t, ...threads.value]
    total.value += 1
    draft.value = { title: '', body: '', is_announcement: false }
    showCreate.value = false
    router.push({ name: 'forum-thread', params: { threadId: t.id } })
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    creating.value = false
  }
}

function openThread(thread: ForumThreadPublic) {
  router.push({ name: 'forum-thread', params: { threadId: thread.id } })
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return formatDateTime(iso, locale.value)
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('forum.title'), t('forum.course_threads')]"
    class="mb-4"
  />

  <div class="mb-6 flex items-end justify-between gap-4 flex-wrap">
    <div>
      <h1 class="page-title mb-1.5">{{ t('forum.course_threads') }}</h1>
      <p class="page-subtitle">{{ courseTitle || t('forum.title') }}</p>
    </div>
    <UiButton @click="showCreate = !showCreate">
      + {{ t('forum.new_thread') }}
    </UiButton>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <!-- Create form -->
  <UiCard v-if="showCreate" class="mb-6 p-4">
    <div class="space-y-3">
      <div>
        <label class="text-[12px] font-mono text-muted-foreground block mb-1">
          {{ t('forum.thread_title_label') }}
        </label>
        <UiInput
          v-model="draft.title"
          :placeholder="t('forum.thread_title_placeholder')"
        />
      </div>
      <div>
        <label class="text-[12px] font-mono text-muted-foreground block mb-1">
          {{ t('forum.thread_body_label') }}
        </label>
        <textarea
          v-model="draft.body"
          rows="4"
          class="w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring"
          :placeholder="t('forum.thread_body_placeholder')"
        ></textarea>
      </div>
      <label v-if="canAnnounce" class="flex items-center gap-2 text-[13px]">
        <input v-model="draft.is_announcement" type="checkbox" />
        <span>
          {{ t('forum.is_announcement') }}
          <span class="text-[12px] text-muted-foreground block">
            {{ t('forum.is_announcement_hint') }}
          </span>
        </span>
      </label>
      <div class="flex gap-2 justify-end">
        <UiButton variant="outline" @click="showCreate = false">
          {{ t('forum.cancel') }}
        </UiButton>
        <UiButton :disabled="creating || !draft.title.trim()" @click="createThread">
          {{ t('forum.create') }}
        </UiButton>
      </div>
    </div>
  </UiCard>

  <!-- Threads list -->
  <div v-if="loading">
    <UiSkeleton :count="5" />
  </div>

  <UiCard
    v-else-if="threads.length === 0"
    class="py-12 text-center text-muted-foreground"
  >
    {{ t('forum.empty_threads') }}
  </UiCard>

  <UiCard v-else no-padding>
    <ul class="divide-y divide-border">
      <li v-for="th in threads" :key="th.id">
        <button
          type="button"
          class="block w-full text-left px-4 py-3 hover:bg-muted/40 transition-colors"
          @click="openThread(th)"
        >
          <div class="flex items-start gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <UiBadge v-if="th.is_pinned" variant="info">
                  {{ t('forum.pinned') }}
                </UiBadge>
                <UiBadge v-if="th.is_announcement" variant="warning">
                  {{ t('forum.announcement') }}
                </UiBadge>
                <UiBadge v-if="th.is_locked" variant="danger">
                  {{ t('forum.locked') }}
                </UiBadge>
                <span class="text-[14px] font-medium">{{ th.title }}</span>
              </div>
              <div class="flex items-center gap-3 text-[12px] text-muted-foreground font-mono">
                <span>{{ t('forum.posts_count', { n: th.post_count }) }}</span>
                <span>·</span>
                <span>{{ t('forum.views_count', { n: th.view_count }) }}</span>
                <span>·</span>
                <span>{{ t('forum.last_reply_at', { date: fmtDate(th.last_reply_at) }) }}</span>
              </div>
            </div>
          </div>
        </button>
      </li>
    </ul>
  </UiCard>
</template>
