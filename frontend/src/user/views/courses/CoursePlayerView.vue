<script setup lang="ts">
/**
 * Wireframe 07 — Lesson Player.
 *
 * Fullscreen shell (no AppLayout):
 *   [320px lesson sidebar] [1fr player area]
 *
 * Sidebar:
 *   ← KURSGA QAYTISH
 *   Course title + course progress bar + %
 *   Module sections (sidebar-section-title) + lesson items (UiCheck + meta)
 *
 * Player area:
 *   Top bar: DARS x/N mono tag + lesson title + prev/next btns
 *   Primary content (LessonContentViewer) — content-type aware: video/text/pdf/file/link
 *   Tabs (Mavzu / Materiallar / Savol-javob)
 *   Content grid 1fr + 280px notes panel (localStorage shaxsiy eslatmalar — Ph.20.4)
 *   Bottom action bar: "Bu darsni tugatdim" checkbox + prev/next
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiCheck from '@shared/components/ui/UiCheck.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import LessonCommentsPanel from '@user/components/LessonCommentsPanel.vue'
import {
  coursesApi,
  lessonsApi,
  modulesApi,
  progressApi,
} from '@shared/api/courses'
import { contentApi } from '@shared/api/content'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { ContentItem } from '@shared/types/content'
import type {
  Course,
  CourseProgress,
  Lesson,
  LessonProgress,
  Module,
} from '@shared/types/courses'
import type { LiveSession } from '@shared/types/live'

import LessonContentViewer from '@user/components/courses/LessonContentViewer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const courseId = computed(() => Number(route.params.id))

const course = ref<Course | null>(null)
const modules = ref<Module[]>([])
const lessonsByModule = ref<Record<number, Lesson[]>>({})
const courseProgress = ref<CourseProgress | null>(null)
const lessonProgressByLesson = ref<Record<number, LessonProgress>>({})

const activeLessonId = ref<number | null>(null)
const activeContent = ref<ContentItem | null>(null)
const contentLoading = ref(false)
const lessonRecordings = ref<LiveSession[]>([])

// Phase 20.3 — kurs bo'yicha yuklab olinadigan materiallar
type Material = { lessonId: number; lessonTitle: string; content: ContentItem }
const materials = ref<Material[]>([])
const materialsLoading = ref(false)
const materialsLoaded = ref(false)
const DOWNLOADABLE_TYPES = ['pdf', 'file', 'link', 'video']

// Phase 20.4 — dars eslatmalari (localStorage, shaxsiy)
const noteText = ref('')
const noteSaved = ref(false)

function noteKey(lessonId: number): string {
  return `lms.notes.${auth.user?.id ?? 'anon'}.${lessonId}`
}

function loadNote(lessonId: number) {
  noteText.value = localStorage.getItem(noteKey(lessonId)) ?? ''
  noteSaved.value = false
}

function saveNote() {
  if (activeLessonId.value === null) return
  localStorage.setItem(noteKey(activeLessonId.value), noteText.value)
  noteSaved.value = true
}

const loading = ref(false)
const error = ref<string | null>(null)
const acting = ref<'start' | 'complete' | null>(null)

type PlayerTab = 'topic' | 'materials' | 'qna'
const activeTab = ref<PlayerTab>('topic')

const flatLessons = computed(() => {
  const out: Lesson[] = []
  for (const m of modules.value) {
    for (const l of lessonsByModule.value[m.id] ?? []) out.push(l)
  }
  return out
})

const activeLesson = computed(
  () => flatLessons.value.find((l) => l.id === activeLessonId.value) ?? null,
)

const activeLessonIndex = computed(() => {
  if (activeLessonId.value === null) return -1
  return flatLessons.value.findIndex((l) => l.id === activeLessonId.value)
})

const prevLesson = computed(() => {
  const idx = activeLessonIndex.value
  return idx > 0 ? flatLessons.value[idx - 1] : null
})

const nextLesson = computed(() => {
  const idx = activeLessonIndex.value
  return idx >= 0 && idx < flatLessons.value.length - 1
    ? flatLessons.value[idx + 1]
    : null
})

const activeLessonProgress = computed(() =>
  activeLessonId.value === null
    ? null
    : lessonProgressByLesson.value[activeLessonId.value] ?? null,
)

const isActiveLessonCompleted = computed(() => {
  const p = activeLessonProgress.value
  if (!p) return false
  return parseFloat(p.progress_percent) >= 100
})

const courseFullyDone = computed(
  () => courseProgress.value?.completion_status === 'completed',
)

const coursePercent = computed(() => {
  const p = courseProgress.value
  if (!p) return 0
  return Math.round(parseFloat(p.percent))
})

const totalLessons = computed(() => flatLessons.value.length)

const tabs = computed(() => [
  { id: 'topic', label: t('player.tab_topic') },
  { id: 'materials', label: t('player.tab_materials') },
  { id: 'qna', label: t('player.tab_qna') },
])

function lessonState(l: Lesson): 'empty' | 'done' | 'locked' {
  const p = lessonProgressByLesson.value[l.id]
  if (p && parseFloat(p.progress_percent) >= 100) return 'done'
  return 'empty'
}

function lessonMetaLabel(l: Lesson): string {
  if (l.estimated_minutes) return t('player.estimated_minutes', { n: l.estimated_minutes })
  return l.is_required_for_completion
    ? t('player.lesson_required')
    : t('player.lesson_optional')
}

async function loadCourseStructure() {
  loading.value = true
  error.value = null
  try {
    const c = await coursesApi.get(courseId.value)
    course.value = c

    const mods = await modulesApi.list(courseId.value)
    modules.value = mods
    const byId: Record<number, Lesson[]> = {}
    await Promise.all(
      mods.map(async (m) => {
        byId[m.id] = await lessonsApi.list(m.id)
      }),
    )
    lessonsByModule.value = byId

    if (activeLessonId.value === null) {
      const requested = Number(route.query.lesson)
      const fromQuery = requested
        ? flatLessons.value.find((l) => l.id === requested)
        : null
      const first = fromQuery ?? flatLessons.value[0]
      if (first) await selectLesson(first.id)
    }

    await refreshCourseProgress()
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'my-learning' })
      return
    }
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function refreshCourseProgress() {
  try {
    courseProgress.value = await progressApi.myCourseProgress(courseId.value)
  } catch {
    courseProgress.value = null
  }
}

async function selectLesson(lessonId: number) {
  activeLessonId.value = lessonId
  activeContent.value = null
  lessonRecordings.value = []
  activeTab.value = 'topic'
  loadNote(lessonId)
  contentLoading.value = true
  try {
    const lesson = flatLessons.value.find((l) => l.id === lessonId)
    if (lesson?.primary_content_id) {
      activeContent.value = await contentApi.get(lesson.primary_content_id)
    }
    try {
      const data = await liveSessionsApi.list({
        lesson_id: lessonId,
        status: 'ended',
        page_size: 20,
      })
      lessonRecordings.value = data.items.filter((s) => !!s.recording_url)
    } catch {
      lessonRecordings.value = []
    }
    if (auth.user) {
      try {
        const lp = await progressApi.start(lessonId)
        lessonProgressByLesson.value = {
          ...lessonProgressByLesson.value,
          [lessonId]: lp,
        }
      } catch {
        // 409 — sukut bilan o'tib ketamiz
      }
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    contentLoading.value = false
  }
}

async function loadMaterials() {
  if (materialsLoaded.value || materialsLoading.value) return
  materialsLoading.value = true
  try {
    const withContent = flatLessons.value.filter((l) => l.primary_content_id)
    const results = await Promise.all(
      withContent.map(async (l) => {
        try {
          const c = await contentApi.get(l.primary_content_id as number)
          return { lessonId: l.id, lessonTitle: l.title, content: c }
        } catch {
          return null
        }
      }),
    )
    materials.value = results.filter(
      (m): m is Material =>
        !!m && !!m.content.file_url && DOWNLOADABLE_TYPES.includes(m.content.type),
    )
    materialsLoaded.value = true
  } finally {
    materialsLoading.value = false
  }
}

function fileSizeLabel(bytes: number | null | undefined): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function fmtRecordingDate(s: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    }).format(new Date(s))
  } catch {
    return s
  }
}

async function completeLesson() {
  if (!activeLessonId.value || isActiveLessonCompleted.value) return
  acting.value = 'complete'
  try {
    const lp = await progressApi.complete(activeLessonId.value)
    lessonProgressByLesson.value = {
      ...lessonProgressByLesson.value,
      [activeLessonId.value]: lp,
    }
    await refreshCourseProgress()
    if (nextLesson.value) {
      await selectLesson(nextLesson.value.id)
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('player.progress_save_failed'))
  } finally {
    acting.value = null
  }
}

function goBackToCourse() {
  router.push({ name: 'course-detail', params: { id: courseId.value } })
}

onMounted(loadCourseStructure)

watch(activeTab, (tab) => {
  if (tab === 'materials') loadMaterials()
})

watch(courseId, async () => {
  activeLessonId.value = null
  activeContent.value = null
  materials.value = []
  materialsLoaded.value = false
  await loadCourseStructure()
})
</script>

<template>
  <!-- Loading / error before structure ready -->
  <div
    v-if="loading && !course"
    class="min-h-screen grid place-items-center bg-background text-muted-foreground"
  >
    {{ t('common.loading') }}
  </div>

  <div
    v-else-if="error && !course"
    class="min-h-screen grid place-items-center bg-background p-8"
  >
    <UiAlert variant="danger">{{ error }}</UiAlert>
  </div>

  <!-- FULLSCREEN PLAYER SHELL (wireframe 07) -->
  <div
    v-else-if="course"
    class="min-h-screen grid grid-cols-1 lg:grid-cols-[320px_1fr] bg-background text-foreground"
  >
    <!-- LESSON SIDEBAR -->
    <aside
      class="border-r border-border bg-background lg:h-screen lg:sticky lg:top-0 lg:overflow-y-auto"
    >
      <!-- Sidebar header -->
      <div class="px-5 py-4 border-b border-border">
        <button
          type="button"
          class="font-mono text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 mb-3 uppercase tracking-wider"
          @click="goBackToCourse"
        >
          ← {{ t('player.back_to_course') }}
        </button>
        <div class="text-[14px] font-semibold leading-snug truncate">
          {{ course.title }}
        </div>
        <div class="flex items-center gap-2 mt-3">
          <UiProgressBar :value="coursePercent" class="flex-1" />
          <span class="font-mono text-[11px] tabular-nums">{{ coursePercent }}%</span>
        </div>
        <!-- Phase 13.15 — Forum tugmasi -->
        <button
          type="button"
          class="mt-3 w-full text-left font-mono text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 uppercase tracking-wider"
          @click="router.push({ name: 'forum-course', params: { courseId: courseId } })"
        >
          → {{ t('player.open_forum') }}
        </button>
      </div>

      <!-- Modules + lessons -->
      <template v-for="(m, mIdx) in modules" :key="m.id">
        <div class="px-5 pt-4 pb-2">
          <div class="sidebar-section-title">
            {{ t('player.module_label') }} {{ mIdx + 1 }} · {{ m.title }}
          </div>
        </div>
        <div>
          <button
            v-for="(l, lIdx) in lessonsByModule[m.id] ?? []"
            :key="l.id"
            type="button"
            class="w-full text-left px-5 py-2.5 flex items-center gap-2.5 border-b border-border transition-colors"
            :class="
              activeLessonId === l.id
                ? 'bg-muted border-l-2 border-l-foreground -ml-px'
                : 'hover:bg-muted/60'
            "
            @click="selectLesson(l.id)"
          >
            <UiCheck :state="lessonState(l)" />
            <div class="flex-1 min-w-0">
              <div
                class="text-[13px] truncate"
                :class="activeLessonId === l.id ? 'font-semibold' : 'font-medium'"
              >
                {{ mIdx + 1 }}.{{ lIdx + 1 }} {{ l.title }}
              </div>
              <div class="font-mono text-[11px] text-muted-foreground mt-0.5 uppercase tracking-wider">
                {{ lessonMetaLabel(l) }}
              </div>
            </div>
          </button>
        </div>
      </template>
    </aside>

    <!-- PLAYER AREA -->
    <div class="flex flex-col min-w-0">
      <!-- Top bar -->
      <div
        class="px-6 lg:px-8 py-3 border-b border-border flex items-center justify-between gap-4 bg-background"
      >
        <div class="min-w-0">
          <div class="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">
            {{ t('player.lesson_label') }}
            {{ activeLessonIndex >= 0 ? activeLessonIndex + 1 : '—' }} / {{ totalLessons }}
          </div>
          <div class="text-[16px] font-semibold truncate mt-0.5">
            {{ activeLesson?.title ?? t('player.no_lesson_selected') }}
          </div>
        </div>
        <div class="flex gap-2 shrink-0">
          <UiButton
            variant="outline"
            size="sm"
            :disabled="!prevLesson"
            @click="prevLesson && selectLesson(prevLesson.id)"
          >
            ← {{ t('player.prev_short') }}
          </UiButton>
          <UiButton
            size="sm"
            :disabled="!nextLesson"
            @click="nextLesson && selectLesson(nextLesson.id)"
          >
            {{ t('player.next_short') }} →
          </UiButton>
        </div>
      </div>

      <UiAlert v-if="error" variant="danger" class="m-6">{{ error }}</UiAlert>

      <UiAlert v-if="courseFullyDone" variant="success" class="m-6">
        {{ t('player.complete_course_done') }}
      </UiAlert>

      <!-- Tabs + content + notes panel -->
      <div class="px-6 lg:px-8 py-8 w-full max-w-[1320px] mx-auto">
        <UiTabs v-model="activeTab" :tabs="tabs" />

        <div class="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6 lg:gap-8">
          <!-- Main column -->
          <div class="min-w-0">
            <!-- TOPIC TAB -->
            <template v-if="activeTab === 'topic' && activeLesson">
              <div class="flex items-center gap-2 mb-3 flex-wrap">
                <UiBadge
                  :variant="
                    activeLesson.is_required_for_completion ? 'default' : 'warning'
                  "
                >
                  {{
                    activeLesson.is_required_for_completion
                      ? t('player.lesson_required')
                      : t('player.lesson_optional')
                  }}
                </UiBadge>
                <span
                  v-if="activeLesson.estimated_minutes"
                  class="font-mono text-[11px] text-muted-foreground"
                >
                  {{ t('player.estimated_minutes', { n: activeLesson.estimated_minutes }) }}
                </span>
                <UiBadge v-if="isActiveLessonCompleted" variant="success" with-dot>
                  {{ t('player.completed_label') }}
                </UiBadge>
              </div>

              <h2
                class="text-[22px] font-semibold tracking-tight mb-4"
              >
                {{ activeLesson.title }}
              </h2>
              <p
                v-if="activeLesson.description"
                class="text-[14px] leading-relaxed text-muted-foreground mb-6"
              >
                {{ activeLesson.description }}
              </p>

              <div v-if="contentLoading" class="text-center py-8 text-muted-foreground">
                {{ t('common.loading') }}
              </div>
              <LessonContentViewer v-else :content="activeContent" />

              <!-- Live recordings (Phase 5d) -->
              <section
                v-if="!contentLoading && lessonRecordings.length > 0"
                class="mt-8 pt-6 border-t border-border"
              >
                <div class="mono-tag mb-3">
                  {{ t('player.recordings_section', { n: lessonRecordings.length }) }}
                </div>
                <div class="space-y-4">
                  <div
                    v-for="rec in lessonRecordings"
                    :key="rec.id"
                    class="border border-border rounded-md overflow-hidden"
                  >
                    <div
                      class="px-4 py-2.5 border-b border-border bg-muted/30 flex items-center justify-between gap-3"
                    >
                      <div class="min-w-0">
                        <div class="text-[13px] font-medium truncate">{{ rec.title }}</div>
                        <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
                          {{ fmtRecordingDate(rec.scheduled_start, $i18n.locale) }}
                        </div>
                      </div>
                    </div>
                    <video
                      :src="rec.recording_url ?? ''"
                      :poster="rec.thumbnail_url ?? undefined"
                      controls
                      preload="metadata"
                      class="w-full max-h-[60vh] bg-foreground"
                    />
                  </div>
                </div>
              </section>
            </template>

            <!-- MATERIALS TAB (Phase 20.3) — kurs bo'yicha yuklab olinadigan resurslar -->
            <template v-else-if="activeTab === 'materials'">
              <div v-if="materialsLoading" class="text-center py-12 text-muted-foreground">
                {{ t('common.loading') }}
              </div>
              <div
                v-else-if="materials.length === 0"
                class="text-center py-16 border border-dashed border-border rounded-lg text-muted-foreground"
              >
                {{ t('player.materials_empty') }}
              </div>
              <ul v-else class="space-y-2.5">
                <li v-for="m in materials" :key="m.content.id">
                  <a
                    :href="m.content.file_url ?? '#'"
                    :download="m.content.type !== 'link' ? '' : undefined"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center gap-3 px-4 py-3 border border-border rounded-md hover:bg-muted/40 transition-colors"
                  >
                    <UiBadge variant="default">
                      {{ t(`content_picker.type_${m.content.type}`) }}
                    </UiBadge>
                    <div class="min-w-0 flex-1">
                      <div class="text-[13px] font-medium truncate">{{ m.content.title }}</div>
                      <div class="font-mono text-[11px] text-muted-foreground truncate">
                        {{ m.lessonTitle }}
                      </div>
                    </div>
                    <span
                      v-if="m.content.file_size"
                      class="font-mono text-[11px] text-muted-foreground shrink-0"
                    >
                      {{ fileSizeLabel(m.content.file_size) }}
                    </span>
                  </a>
                </li>
              </ul>
            </template>

            <!-- Q&A TAB (Phase 20.2) — dars izohlari/savol-javoblar -->
            <template v-else-if="activeTab === 'qna'">
              <LessonCommentsPanel v-if="activeLessonId" :lesson-id="activeLessonId" />
            </template>
          </div>

          <!-- Notes panel (Phase 20.4 — localStorage, shaxsiy) -->
          <aside class="space-y-4">
            <UiCard no-padding>
              <div class="px-4 py-3 border-b border-border flex items-center justify-between">
                <span class="text-[13px] font-semibold">{{ t('player.notes_title') }}</span>
                <span
                  v-if="noteSaved"
                  class="font-mono text-[10px] text-success uppercase tracking-wider"
                >
                  {{ t('player.notes_saved') }}
                </span>
              </div>
              <div class="p-3">
                <textarea
                  v-model="noteText"
                  :disabled="activeLessonId === null"
                  :placeholder="t('player.notes_placeholder')"
                  rows="9"
                  class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-[13px] leading-relaxed focus:outline-none focus:ring-1 focus:ring-foreground/30 disabled:opacity-50"
                  @input="noteSaved = false"
                  @blur="saveNote"
                ></textarea>
                <UiButton
                  size="sm"
                  class="w-full justify-center mt-2"
                  :disabled="activeLessonId === null"
                  @click="saveNote"
                >
                  {{ t('player.notes_save') }}
                </UiButton>
                <p class="font-mono text-[10px] text-muted-foreground mt-2 leading-relaxed">
                  {{ t('player.notes_local_hint') }}
                </p>
              </div>
            </UiCard>
          </aside>
        </div>

        <!-- Bottom action bar -->
        <div
          class="mt-8 pt-6 border-t border-border flex flex-wrap justify-between items-center gap-3"
        >
          <label class="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              class="w-[18px] h-[18px] accent-foreground cursor-pointer"
              :checked="isActiveLessonCompleted"
              :disabled="isActiveLessonCompleted || acting === 'complete'"
              @change="completeLesson"
            />
            <span class="text-[14px] font-medium">{{ t('player.mark_done_label') }}</span>
          </label>
          <div class="flex gap-2">
            <UiButton
              variant="outline"
              :disabled="!prevLesson"
              @click="prevLesson && selectLesson(prevLesson.id)"
            >
              ← {{ prevLesson?.title ?? t('player.prev_lesson') }}
            </UiButton>
            <UiButton
              :disabled="!nextLesson"
              @click="nextLesson && selectLesson(nextLesson.id)"
            >
              {{ nextLesson?.title ?? t('player.next_lesson') }} →
            </UiButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
