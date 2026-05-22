<script setup lang="ts">
/**
 * Wireframe 06 — Course Detail (talaba).
 *
 * Hero (1fr + 320px sticky):
 *   - Badges (course-category + status) + h1 + description
 *   - 4-column meta strip: teacher / duration / level / certificate
 *   - Right card: cover, your-progress bar, "Davom etish" / "Yozilish",
 *     download materials, key dates
 * Tabs (Modullar / Sillabus / O'qituvchi / Forum / Sharhlar) — modules only,
 *   rest are Phase 6+ placeholders.
 * Modules grid (1fr + 320px right):
 *   - Module cards: completed (✓ green ring) / active (foreground ring + number) / locked (🔒 gray)
 *     - Active module expands to show lesson list with status icons + meta
 *   - Right sidebar: Materials card (top 3 attached contents) + Statistics card
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiImagePlaceholder from '@shared/components/ui/UiImagePlaceholder.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import {
  coursesApi,
  enrollmentsApi,
  lessonsApi,
  modulesApi,
  progressApi,
} from '@shared/api/courses'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type {
  Course,
  CourseProgress,
  Lesson,
  LessonProgress,
  Module,
} from '@shared/types/courses'

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
const isEnrolled = ref(false)
const studentCount = ref<number | null>(null)

const loading = ref(false)
const enrolling = ref(false)
const error = ref<string | null>(null)

type DetailTab = 'modules' | 'syllabus' | 'teacher' | 'forum' | 'reviews'
const activeTab = ref<DetailTab>('modules')

const expandedModuleId = ref<number | null>(null)

const flatLessons = computed(() => {
  const out: Lesson[] = []
  for (const m of modules.value) {
    for (const l of lessonsByModule.value[m.id] ?? []) out.push(l)
  }
  return out
})

const completedLessonsCount = computed(
  () => courseProgress.value?.completed_lessons ?? 0,
)

const totalRequiredLessons = computed(
  () => courseProgress.value?.total_required_lessons ?? flatLessons.value.length,
)

const coursePercent = computed(() => {
  const p = courseProgress.value
  if (!p) return 0
  return Math.round(parseFloat(p.percent))
})

const heroBadges = computed(() => {
  const out: { label: string; variant?: 'info' | 'success' | 'warning' }[] = []
  if (course.value?.type) {
    out.push({ label: t(`courses.type_${course.value.type}`).toUpperCase() })
  }
  if (course.value?.status === 'published') {
    out.push({ label: t('course_detail.status_active'), variant: 'info' })
  }
  return out
})

const metaItems = computed(() => {
  const c = course.value
  if (!c) return []
  return [
    {
      label: t('course_detail.meta_teacher'),
      value: t('course_detail.teacher_placeholder'),
      sub: t('course_detail.teacher_role_placeholder'),
    },
    {
      label: t('course_detail.meta_duration'),
      value: c.duration_weeks
        ? `${c.duration_weeks} ${t('course_detail.weeks')}`
        : '—',
      sub: c.estimated_hours ? `~${c.estimated_hours} ${t('course_detail.hours')}` : '',
    },
    {
      label: t('course_detail.meta_level'),
      value: c.level ? t(`courses.level_${c.level}`) : '—',
      sub: t('course_detail.level_sub_placeholder'),
    },
    {
      label: t('course_detail.meta_certificate'),
      value: t('course_detail.certificate_available'),
      sub: t('course_detail.certificate_sub'),
    },
  ]
})

const tabs = computed(() => [
  {
    id: 'modules',
    label: t('course_detail.tab_modules'),
    count: modules.value.length,
  },
  { id: 'syllabus', label: t('course_detail.tab_syllabus'), disabled: true },
  { id: 'teacher', label: t('course_detail.tab_teacher'), disabled: true },
  // Phase 13.14 — Forum tabi kurs a'zolari uchun ochiq (RBAC backendda)
  {
    id: 'forum',
    label: t('course_detail.tab_forum'),
    disabled: !isEnrolled.value,
  },
  { id: 'reviews', label: t('course_detail.tab_reviews'), disabled: true },
])

interface ModuleStats {
  totalLessons: number
  completedLessons: number
  percent: number
  estimatedMinutes: number
  state: 'completed' | 'active' | 'locked' | 'available'
}

function getModuleStats(m: Module): ModuleStats {
  const lessons = lessonsByModule.value[m.id] ?? []
  let completed = 0
  let estimated = 0
  for (const l of lessons) {
    estimated += l.estimated_minutes ?? 0
    const p = lessonProgressByLesson.value[l.id]
    if (p && parseFloat(p.progress_percent) >= 100) completed++
  }
  const total = lessons.length
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)
  let state: ModuleStats['state'] = 'available'
  if (percent === 100 && total > 0) state = 'completed'
  else if (percent > 0) state = 'active'
  return { totalLessons: total, completedLessons: completed, percent, estimatedMinutes: estimated, state }
}

function fmtMinutes(min: number): string {
  if (min <= 0) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h > 0 && m > 0) return `${h}${t('course_detail.hour_short')} ${m}${t('course_detail.min_short')}`
  if (h > 0) return `${h}${t('course_detail.hour_short')}`
  return `${m}${t('course_detail.min_short')}`
}

function fmtDate(s: string | null): string {
  if (!s) return '—'
  try {
    return new Intl.DateTimeFormat('uz-Latn', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date(s))
  } catch {
    return s
  }
}

function lessonState(l: Lesson): 'done' | 'active' | 'locked' {
  const p = lessonProgressByLesson.value[l.id]
  if (p && parseFloat(p.progress_percent) >= 100) return 'done'
  if (p) return 'active'
  return 'locked'
}

async function load() {
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

    if (auth.user) {
      try {
        const my = await coursesApi.list({
          enrolled_user_id: auth.user.id,
          page_size: 100,
        })
        isEnrolled.value = my.items.some((x) => x.id === courseId.value)
      } catch {
        isEnrolled.value = false
      }
    }

    if (isEnrolled.value) {
      try {
        courseProgress.value = await progressApi.myCourseProgress(courseId.value)
      } catch {
        courseProgress.value = null
      }
    }

    // Auto-expand first non-completed module
    for (const m of mods) {
      const stats = getModuleStats(m)
      if (stats.state !== 'completed') {
        expandedModuleId.value = m.id
        break
      }
    }
    if (expandedModuleId.value === null && mods.length > 0) {
      expandedModuleId.value = mods[0].id
    }

    try {
      const stData = await enrollmentsApi.listStudents(courseId.value, { page_size: 1 })
      studentCount.value = stData.total
    } catch {
      studentCount.value = null
    }
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

function toggleModule(m: Module) {
  expandedModuleId.value = expandedModuleId.value === m.id ? null : m.id
}

function openPlayer(lesson?: Lesson) {
  router.push({
    name: 'course-player',
    params: { id: courseId.value },
    ...(lesson ? { query: { lesson: lesson.id } } : {}),
  })
}

async function handleEnroll() {
  if (!course.value || course.value.enrollment_type !== 'self') return
  enrolling.value = true
  try {
    await enrollmentsApi.selfEnroll(courseId.value)
    isEnrolled.value = true
    try {
      courseProgress.value = await progressApi.myCourseProgress(courseId.value)
    } catch {
      courseProgress.value = null
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    enrolling.value = false
  }
}

onMounted(load)

watch(courseId, async () => {
  expandedModuleId.value = null
  course.value = null
  modules.value = []
  lessonsByModule.value = {}
  await load()
})
</script>

<template>
  <div v-if="loading && !course" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !course" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="course">
    <!-- Breadcrumb -->
    <UiBreadcrumb
      :items="[
        t('dashboard.crumb_home'),
        t('learning.title'),
        course.title,
      ]"
      class="mb-6"
    />

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <!-- HERO: left content + right sticky enroll/progress card -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 mb-6">
      <div>
        <div class="flex flex-wrap gap-2 mb-3">
          <UiBadge
            v-for="(b, i) in heroBadges"
            :key="i"
            :variant="b.variant ?? 'default'"
            :with-dot="b.variant === 'info'"
          >
            {{ b.label }}
          </UiBadge>
          <UiBadge v-if="course.language">{{ course.language.toUpperCase() }}</UiBadge>
        </div>
        <h1
          class="text-[32px] font-semibold tracking-tightest leading-tight mb-3"
        >
          {{ course.title }}
        </h1>
        <p
          v-if="course.description"
          class="text-[15px] leading-relaxed text-muted-foreground mb-5"
        >
          {{ course.description }}
        </p>

        <!-- Meta strip (4-col) -->
        <div
          class="grid grid-cols-2 md:grid-cols-4 gap-4 p-5 border border-border rounded-lg bg-card"
        >
          <div
            v-for="(item, i) in metaItems"
            :key="i"
            class="md:border-r md:border-border md:last:border-r-0 md:pr-4"
          >
            <div
              class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mb-1"
            >
              {{ item.label }}
            </div>
            <div class="font-medium text-[14px]">{{ item.value }}</div>
            <div v-if="item.sub" class="text-[12px] text-muted-foreground">
              {{ item.sub }}
            </div>
          </div>
        </div>
      </div>

      <!-- Right card (sticky) -->
      <UiCard no-padding class="self-start lg:sticky lg:top-6">
        <UiImagePlaceholder label="COURSE COVER" aspect="16/9" class="rounded-t-lg" />
        <div class="p-5">
          <template v-if="isEnrolled">
            <div class="mb-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-[13px] font-medium">{{ t('course_detail.your_progress') }}</span>
                <span class="font-mono text-[13px] font-semibold tabular-nums">
                  {{ coursePercent }}%
                </span>
              </div>
              <UiProgressBar :value="coursePercent" />
              <div class="text-[11px] text-muted-foreground mt-2">
                {{ t('course_detail.lessons_done', {
                  done: completedLessonsCount,
                  total: totalRequiredLessons,
                }) }}
              </div>
            </div>
            <UiButton class="w-full justify-center mb-2" @click="openPlayer()">
              ▶ {{ coursePercent > 0 ? t('course_detail.continue') : t('course_detail.start') }}
            </UiButton>
            <UiButton variant="outline" class="w-full justify-center" disabled>
              📥 {{ t('course_detail.download_materials') }}
              <span class="font-mono text-[10px] text-muted-foreground ml-1">Ph.6</span>
            </UiButton>
          </template>

          <template v-else>
            <div class="text-[13px] text-muted-foreground mb-3">
              {{ t('course_detail.not_enrolled_hint') }}
            </div>
            <UiButton
              v-if="course.enrollment_type === 'self'"
              class="w-full justify-center mb-2"
              :loading="enrolling"
              @click="handleEnroll"
            >
              {{ t('catalog.enroll') }}
            </UiButton>
            <UiButton v-else variant="outline" class="w-full justify-center" disabled>
              {{ t('catalog.manual_enroll_badge') }}
            </UiButton>
          </template>

          <div class="mt-5 pt-5 border-t border-border text-[12px] space-y-2">
            <div class="flex justify-between">
              <span class="text-muted-foreground">{{ t('course_detail.started_at') }}:</span>
              <span class="font-mono">{{ fmtDate(course.published_at) }}</span>
            </div>
            <div v-if="course.duration_weeks" class="flex justify-between">
              <span class="text-muted-foreground">{{ t('course_detail.duration') }}:</span>
              <span class="font-mono">
                {{ course.duration_weeks }} {{ t('course_detail.weeks') }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">{{ t('course_detail.students') }}:</span>
              <span class="font-mono">{{ studentCount ?? '—' }}</span>
            </div>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- TABS -->
    <UiTabs v-model="activeTab" :tabs="tabs" />

    <!-- MODULES TAB -->
    <div
      v-if="activeTab === 'modules'"
      class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6"
    >
      <!-- Modules list -->
      <div class="flex flex-col gap-3">
        <div
          v-if="modules.length === 0"
          class="text-center py-12 text-muted-foreground border border-dashed border-border rounded-lg"
        >
          {{ t('course_detail.no_modules') }}
        </div>

        <template v-for="(m, mIdx) in modules" :key="m.id">
          <UiCard
            no-padding
            :class="
              expandedModuleId === m.id
                ? 'border-foreground'
                : getModuleStats(m).state === 'completed'
                  ? ''
                  : 'opacity-90'
            "
          >
            <button
              type="button"
              class="w-full text-left px-5 py-4 flex items-center gap-4"
              @click="toggleModule(m)"
            >
              <!-- Module status ring -->
              <span
                class="w-8 h-8 rounded-full grid place-items-center font-mono text-[12px] font-semibold flex-shrink-0"
                :class="
                  getModuleStats(m).state === 'completed'
                    ? 'bg-success-500 border-2 border-success-500 text-white'
                    : 'bg-background border-2 border-foreground text-foreground'
                "
              >
                <template v-if="getModuleStats(m).state === 'completed'">✓</template>
                <template v-else>{{ String(mIdx + 1).padStart(2, '0') }}</template>
              </span>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <span
                    class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground"
                  >
                    {{ t('course_detail.module_label') }} {{ mIdx + 1 }}
                  </span>
                  <UiBadge
                    v-if="getModuleStats(m).state === 'completed'"
                    variant="success"
                  >
                    {{ t('course_detail.module_completed') }}
                  </UiBadge>
                  <UiBadge
                    v-else-if="getModuleStats(m).state === 'active'"
                    variant="info"
                    with-dot
                  >
                    {{ t('course_detail.module_now') }}
                  </UiBadge>
                </div>
                <div class="font-semibold text-[15px] truncate">{{ m.title }}</div>
                <div class="text-[12px] text-muted-foreground mt-0.5">
                  {{ getModuleStats(m).totalLessons }} {{ t('course_detail.lessons_short') }}
                  · {{ fmtMinutes(getModuleStats(m).estimatedMinutes) }}
                </div>
              </div>
              <span
                class="font-mono text-[12px] flex-shrink-0"
                :class="
                  expandedModuleId === m.id
                    ? 'font-semibold text-foreground'
                    : 'text-muted-foreground'
                "
              >
                {{ getModuleStats(m).percent }}%
              </span>
            </button>

            <!-- Lessons list (when expanded) -->
            <div v-if="expandedModuleId === m.id" class="border-t border-border">
              <button
                v-for="(l, lIdx) in lessonsByModule[m.id] ?? []"
                :key="l.id"
                type="button"
                class="w-full text-left flex items-center gap-3 px-5 py-3 border-b border-border last:border-b-0 hover:bg-muted/50"
                @click="openPlayer(l)"
              >
                <span class="w-8 text-center font-mono text-[11px] text-muted-foreground">
                  {{ mIdx + 1 }}.{{ lIdx + 1 }}
                </span>
                <span class="w-5 h-5 grid place-items-center flex-shrink-0">
                  <span
                    v-if="lessonState(l) === 'done'"
                    class="text-success-600"
                  >✓</span>
                  <span
                    v-else-if="lessonState(l) === 'active'"
                    class="w-4 h-4 rounded-full border-2 border-foreground bg-foreground text-background grid place-items-center text-[9px]"
                  >▶</span>
                  <span
                    v-else
                    class="w-4 h-4 rounded-full border border-border-strong"
                    aria-hidden="true"
                  ></span>
                </span>
                <span class="flex-1 text-[13px] truncate">
                  {{ l.title }}
                </span>
                <span class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
                  <template v-if="l.estimated_minutes">
                    {{ l.estimated_minutes }} {{ t('course_detail.min_label') }} ·
                  </template>
                  {{ t('player.content_video') }}
                </span>
              </button>
            </div>
          </UiCard>
        </template>
      </div>

      <!-- Right sidebar: Materials + Statistics -->
      <aside class="flex flex-col gap-4">
        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border flex items-center justify-between">
            <span class="text-[13px] font-semibold">{{ t('course_detail.materials_title') }}</span>
            <UiBadge>—</UiBadge>
          </div>
          <div class="text-center text-[12px] text-muted-foreground px-5 py-6">
            {{ t('course_detail.materials_empty') }}
            <div class="font-mono text-[10px] mt-1 uppercase tracking-wider">Phase 6+</div>
          </div>
        </UiCard>

        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border">
            <span class="text-[13px] font-semibold">{{ t('course_detail.stats_title') }}</span>
          </div>
          <div class="px-5 py-3 text-[12px]">
            <div class="flex justify-between py-1.5 border-b border-border">
              <span class="text-muted-foreground">{{ t('course_detail.stats_lessons_done') }}</span>
              <span class="font-mono font-semibold tabular-nums">
                {{ completedLessonsCount }} / {{ totalRequiredLessons }}
              </span>
            </div>
            <div class="flex justify-between py-1.5 border-b border-border">
              <span class="text-muted-foreground">{{ t('course_detail.stats_avg_grade') }}</span>
              <span class="font-mono font-semibold">— <span class="text-[10px]">Ph.6</span></span>
            </div>
            <div class="flex justify-between py-1.5 border-b border-border">
              <span class="text-muted-foreground">{{ t('course_detail.stats_time_spent') }}</span>
              <span class="font-mono font-semibold">— <span class="text-[10px]">Ph.6</span></span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-muted-foreground">{{ t('course_detail.stats_attendance') }}</span>
              <span class="font-mono font-semibold">— <span class="text-[10px]">Ph.6</span></span>
            </div>
          </div>
        </UiCard>
      </aside>
    </div>

    <!-- Phase 13.14 — Forum tab: kurs muhokamasi -->
    <div v-else-if="activeTab === 'forum'" class="space-y-3">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h2 class="text-[16px] font-semibold mb-0.5">
            {{ t('forum.course_threads') }}
          </h2>
          <p class="text-[12px] text-muted-foreground">
            {{ t('forum.title') }} · {{ course?.title }}
          </p>
        </div>
        <UiButton
          variant="outline"
          size="sm"
          @click="router.push({ name: 'forum-course', params: { courseId } })"
        >
          {{ t('course_detail.open_forum') }} →
        </UiButton>
      </div>
      <UiCard class="p-6 text-center text-muted-foreground text-[13px]">
        {{ t('course_detail.forum_hint') }}
      </UiCard>
    </div>

    <!-- Other tabs — placeholders -->
    <div
      v-else
      class="text-center py-16 border border-dashed border-border rounded-lg"
    >
      <div
        class="font-mono text-[11px] uppercase tracking-widest text-muted-foreground mb-2"
      >
        Phase 6+
      </div>
      <p class="text-muted-foreground">{{ t('course_detail.tab_coming_soon') }}</p>
    </div>
  </template>
</template>
