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
  courseMaterialsApi,
  courseTeacherApi,
  courseUpcomingApi,
  coursesApi,
  enrollmentsApi,
  gradebookApi,
  lessonsApi,
  modulesApi,
  progressApi,
  type CourseMaterial,
  type CourseTeacher,
  type GradebookRow,
  type UpcomingExamItem,
  type UpcomingLiveItem,
} from '@shared/api/courses'
import { forumApi, type ForumThreadPublic } from '@shared/api/forum'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { usePermissions } from '@shared/composables/usePermissions'
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
const { hasPermission } = usePermissions()

const courseId = computed(() => Number(route.params.id))

const course = ref<Course | null>(null)
const modules = ref<Module[]>([])
const lessonsByModule = ref<Record<number, Lesson[]>>({})
const courseProgress = ref<CourseProgress | null>(null)
const lessonProgressByLesson = ref<Record<number, LessonProgress>>({})
const isEnrolled = ref(false)
const studentCount = ref<number | null>(null)
const teacher = ref<CourseTeacher | null>(null)
const materials = ref<CourseMaterial[]>([])
const gradebookRow = ref<GradebookRow | null>(null)
const upcomingExams = ref<UpcomingExamItem[]>([])
const upcomingLive = ref<UpcomingLiveItem[]>([])
const forumThreads = ref<ForumThreadPublic[]>([])
const forumLoading = ref(false)

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
    out.push({ label: t(`courses.type_${course.value.type}`) })
  }
  if (course.value?.status === 'published') {
    out.push({ label: t('course_detail.status_active'), variant: 'info' })
  }
  return out
})

const courseLanguageLabel = computed(() => {
  const lang = course.value?.language
  if (!lang) return ''
  const key = `locale.${lang}`
  const translated = t(key)
  return translated === key ? lang : translated
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
  {
    id: 'syllabus',
    label: t('course_detail.tab_syllabus'),
  },
  { id: 'teacher', label: t('course_detail.tab_teacher') },
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

    // Faqat o'qituvchi/admin uchun (talabada `enrollment.read` permission yo'q,
    // shu sababli 403 chiqib ketmasin)
    if (hasPermission('enrollment.read')) {
      try {
        const stData = await enrollmentsApi.listStudents(courseId.value, { page_size: 1 })
        studentCount.value = stData.total
      } catch {
        studentCount.value = null
      }
    } else {
      studentCount.value = null
    }

    // Phase 18.2 — kurs pedagog'i (xato bo'lsa yutamiz)
    try {
      teacher.value = await courseTeacherApi.get(courseId.value)
    } catch {
      teacher.value = null
    }

    // Phase 18.3 — kurs materiallari (lesson content_items)
    try {
      materials.value = await courseMaterialsApi.list(courseId.value)
    } catch {
      materials.value = []
    }

    // Phase 18.4 — gradebook (kurs avg / total ball)
    try {
      const rows = await gradebookApi.myGradebook()
      gradebookRow.value =
        rows.find((r) => r.course_id === courseId.value) ?? null
    } catch {
      gradebookRow.value = null
    }

    // Phase 18.5 — yaqin imtihonlar + live darslar (right column widgetlari)
    try {
      const [examsRes, liveRes] = await Promise.all([
        courseUpcomingApi.exams(courseId.value, 5),
        courseUpcomingApi.live(courseId.value, 5),
      ])
      upcomingExams.value = examsRes
      upcomingLive.value = liveRes
    } catch {
      upcomingExams.value = []
      upcomingLive.value = []
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

// Phase 18.3 — materiallar (faqat content_id'siz lessonlarni filtrlaymiz)
const materialsWithContent = computed(() =>
  materials.value.filter((m) => m.content_id !== null && m.file_url !== null),
)

// Phase 18.4 — Statistics card real qiymatlari
const avgGradeDisplay = computed<string | null>(() => {
  const row = gradebookRow.value
  if (!row) return null
  const total = parseFloat(row.total)
  if (!isFinite(total) || total <= 0) return null
  return `${total.toFixed(1)}%`
})

const timeSpentMinutes = computed<number>(() => {
  let totalSeconds = 0
  let hasTrackedTime = false
  for (const lesson of flatLessons.value) {
    const lp = lessonProgressByLesson.value[lesson.id]
    if (!lp) continue
    if (lp.time_spent_seconds > 0) {
      totalSeconds += lp.time_spent_seconds
      hasTrackedTime = true
    } else if (lp.completed_at) {
      totalSeconds += (lesson.estimated_minutes ?? 0) * 60
    }
  }
  if (!hasTrackedTime && totalSeconds === 0) return 0
  return Math.round(totalSeconds / 60)
})

const timeSpentDisplay = computed<string>(() => {
  const m = timeSpentMinutes.value
  if (m <= 0) return '0' + t('course_detail.min_short')
  const h = Math.floor(m / 60)
  const min = m % 60
  if (h <= 0) return `${min}${t('course_detail.min_short')}`
  if (min === 0) return `${h}${t('course_detail.hour_short')}`
  return `${h}${t('course_detail.hour_short')} ${min}${t('course_detail.min_short')}`
})

const attendanceDisplay = computed<string>(() => {
  const total = totalRequiredLessons.value
  const done = completedLessonsCount.value
  if (total <= 0) return '0%'
  return `${Math.round((done / total) * 100)}%`
})

function materialIcon(type: string | null): string {
  switch (type) {
    case 'video':
      return '🎬'
    case 'pdf':
      return '📄'
    case 'link':
      return '🔗'
    case 'file':
      return '📦'
    case 'scorm':
      return '🎓'
    default:
      return '📑'
  }
}

function fmtExamDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function liveStatusLabel(status: string): string {
  switch (status) {
    case 'live':
      return t('course_detail.live_status_live')
    case 'scheduled':
      return t('course_detail.live_status_scheduled')
    default:
      return status
  }
}

function liveStatusVariant(status: string): 'info' | 'success' | 'warning' {
  if (status === 'live') return 'success'
  return 'info'
}

function downloadAllMaterials() {
  const items = materialsWithContent.value
  if (items.length === 0) return
  items.forEach((m, idx) => {
    if (!m.file_url) return
    // Brauzerni ortiqcha yuklamaslik uchun har bir click'ni biroz kechiktiramiz
    setTimeout(() => {
      const a = document.createElement('a')
      a.href = m.file_url as string
      a.download = m.title || m.lesson_title || `material-${m.lesson_id}`
      a.target = '_blank'
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }, idx * 250)
  })
}

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
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

async function loadForumPreview() {
  forumLoading.value = true
  try {
    const res = await forumApi.listThreads(courseId.value, { page: 1, page_size: 3 })
    forumThreads.value = res.items ?? []
  } catch {
    forumThreads.value = []
  } finally {
    forumLoading.value = false
  }
}

function fmtRelativeDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  const now = Date.now()
  const diffMs = now - d.getTime()
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return t('course_detail.just_now')
  if (diffMin < 60) return t('course_detail.minutes_ago', { n: diffMin })
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return t('course_detail.hours_ago', { n: diffHr })
  const diffDay = Math.round(diffHr / 24)
  if (diffDay < 7) return t('course_detail.days_ago', { n: diffDay })
  return d.toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

onMounted(load)

watch(courseId, async () => {
  expandedModuleId.value = null
  course.value = null
  modules.value = []
  lessonsByModule.value = {}
  forumThreads.value = []
  await load()
})

watch(activeTab, (tab) => {
  if (tab === 'forum' && forumThreads.value.length === 0 && !forumLoading.value) {
    loadForumPreview()
  }
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
          <UiBadge v-if="course.language">{{ courseLanguageLabel }}</UiBadge>
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
            <UiButton
              variant="outline"
              class="w-full justify-center"
              :disabled="materialsWithContent.length === 0"
              @click="downloadAllMaterials"
            >
              📥 {{ t('course_detail.download_materials') }}
              <span
                v-if="materialsWithContent.length"
                class="font-mono text-[10px] text-muted-foreground ml-1"
              >
                ({{ materialsWithContent.length }})
              </span>
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
        <!-- Phase 18.3 — Materials real (lesson content_items) -->
        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border flex items-center justify-between">
            <span class="text-[13px] font-semibold">{{ t('course_detail.materials_title') }}</span>
            <UiBadge>{{ materialsWithContent.length }}</UiBadge>
          </div>
          <div
            v-if="materialsWithContent.length === 0"
            class="text-center text-[12px] text-muted-foreground px-5 py-6"
          >
            {{ t('course_detail.materials_empty_real') }}
          </div>
          <ul v-else class="divide-y divide-border max-h-[360px] overflow-y-auto">
            <li v-for="m in materialsWithContent" :key="m.lesson_id" class="px-4 py-2.5">
              <div class="flex items-start gap-2">
                <span class="text-[16px] shrink-0 mt-0.5">{{ materialIcon(m.type) }}</span>
                <div class="flex-1 min-w-0">
                  <div class="text-[13px] font-medium truncate">
                    {{ m.title || m.lesson_title }}
                  </div>
                  <div class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                    {{ m.type }}
                    <span v-if="m.file_size">· {{ fmtBytes(m.file_size) }}</span>
                  </div>
                </div>
                <a
                  v-if="m.file_url"
                  :href="m.file_url"
                  target="_blank"
                  rel="noopener"
                  class="text-muted-foreground hover:text-foreground shrink-0"
                  :title="t('course_detail.material_download')"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <path d="M7 10l5 5 5-5" />
                    <path d="M12 15V3" />
                  </svg>
                </a>
              </div>
            </li>
          </ul>
        </UiCard>

        <!-- Phase 18.6 — Yaqin imtihonlar widget -->
        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border flex items-center justify-between">
            <span class="text-[13px] font-semibold">{{ t('course_detail.upcoming_exams_title') }}</span>
            <UiBadge v-if="upcomingExams.length">{{ upcomingExams.length }}</UiBadge>
          </div>
          <div
            v-if="upcomingExams.length === 0"
            class="text-center text-[12px] text-muted-foreground px-5 py-6"
          >
            {{ t('course_detail.upcoming_exams_empty') }}
          </div>
          <ul v-else class="divide-y divide-border">
            <li v-for="e in upcomingExams" :key="e.id" class="px-4 py-2.5">
              <div class="flex items-start gap-2">
                <span class="text-[16px] shrink-0 mt-0.5">📝</span>
                <div class="flex-1 min-w-0">
                  <div class="text-[13px] font-medium truncate">{{ e.title }}</div>
                  <div class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                    {{ t(`course_detail.exam_type_${e.type}`, e.type) }}
                    · {{ e.duration_minutes }}{{ t('course_detail.min_short') }}
                  </div>
                  <div class="text-[11px] text-muted-foreground mt-0.5">
                    {{ t('course_detail.exam_available_from') }}: {{ fmtExamDate(e.available_from) }}
                  </div>
                </div>
                <UiBadge v-if="e.proctoring_enabled" variant="warning">
                  {{ t('course_detail.proctoring_short') }}
                </UiBadge>
              </div>
            </li>
          </ul>
        </UiCard>

        <!-- Phase 18.7 — Yaqin live darslar widget -->
        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border flex items-center justify-between">
            <span class="text-[13px] font-semibold">{{ t('course_detail.upcoming_live_title') }}</span>
            <UiBadge v-if="upcomingLive.length">{{ upcomingLive.length }}</UiBadge>
          </div>
          <div
            v-if="upcomingLive.length === 0"
            class="text-center text-[12px] text-muted-foreground px-5 py-6"
          >
            {{ t('course_detail.upcoming_live_empty') }}
          </div>
          <ul v-else class="divide-y divide-border">
            <li v-for="s in upcomingLive" :key="s.id" class="px-4 py-2.5">
              <div class="flex items-start gap-2">
                <span class="text-[16px] shrink-0 mt-0.5">🎥</span>
                <div class="flex-1 min-w-0">
                  <div class="text-[13px] font-medium truncate">{{ s.title }}</div>
                  <div class="text-[11px] text-muted-foreground mt-0.5 truncate">
                    {{ s.host_full_name || t('course_detail.teacher_unknown') }}
                  </div>
                  <div class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                    {{ fmtExamDate(s.scheduled_start) }}
                    · {{ s.duration_minutes }}{{ t('course_detail.min_short') }}
                  </div>
                </div>
                <UiBadge :variant="liveStatusVariant(s.status)">
                  {{ liveStatusLabel(s.status) }}
                </UiBadge>
              </div>
            </li>
          </ul>
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
              <span class="font-mono font-semibold tabular-nums">
                {{ avgGradeDisplay ?? '—' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5 border-b border-border">
              <span class="text-muted-foreground">{{ t('course_detail.stats_time_spent') }}</span>
              <span class="font-mono font-semibold tabular-nums">
                {{ timeSpentDisplay }}
              </span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-muted-foreground">{{ t('course_detail.stats_attendance') }}</span>
              <span class="font-mono font-semibold tabular-nums">
                {{ attendanceDisplay }}
              </span>
            </div>
          </div>
        </UiCard>
      </aside>
    </div>

    <!-- Phase 18.1 — Sillabus tab: maqsadlar, ko'nikmalar, kurs xulosasi -->
    <div
      v-else-if="activeTab === 'syllabus'"
      class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6"
    >
      <div class="space-y-5">
        <!-- Kurs haqida -->
        <UiCard class="p-5">
          <h2 class="text-[16px] font-semibold mb-3">
            {{ t('course_detail.syllabus_about') }}
          </h2>
          <p
            v-if="course.description"
            class="text-[14px] leading-relaxed text-foreground whitespace-pre-line"
          >
            {{ course.description }}
          </p>
          <p
            v-else
            class="text-[13px] text-muted-foreground italic"
          >
            {{ t('course_detail.syllabus_about_empty') }}
          </p>
        </UiCard>

        <!-- Maqsadlar (objectives) -->
        <UiCard class="p-5">
          <h2 class="text-[16px] font-semibold mb-3">
            {{ t('course_detail.syllabus_objectives') }}
          </h2>
          <ul
            v-if="course.objectives && course.objectives.length > 0"
            class="space-y-2"
          >
            <li
              v-for="(obj, i) in course.objectives"
              :key="i"
              class="flex items-start gap-3 text-[14px]"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-success-600 mt-0.5 shrink-0"
              >
                <path d="m9 12 2 2 4-4" />
                <circle cx="12" cy="12" r="10" />
              </svg>
              <span>{{ obj }}</span>
            </li>
          </ul>
          <p v-else class="text-[13px] text-muted-foreground italic">
            {{ t('course_detail.syllabus_objectives_empty') }}
          </p>
        </UiCard>

        <!-- Olinadigan ko'nikmalar (skills_gained) -->
        <UiCard class="p-5">
          <h2 class="text-[16px] font-semibold mb-3">
            {{ t('course_detail.syllabus_skills') }}
          </h2>
          <div
            v-if="course.skills_gained && course.skills_gained.length > 0"
            class="flex flex-wrap gap-2"
          >
            <UiBadge
              v-for="(skill, i) in course.skills_gained"
              :key="i"
              variant="default"
              class="!text-[13px] !py-1 !px-2.5"
            >
              {{ skill }}
            </UiBadge>
          </div>
          <p v-else class="text-[13px] text-muted-foreground italic">
            {{ t('course_detail.syllabus_skills_empty') }}
          </p>
        </UiCard>
      </div>

      <!-- Right sidebar: course summary -->
      <aside class="flex flex-col gap-4">
        <UiCard class="p-5">
          <h3 class="text-[13px] font-semibold mb-3 uppercase tracking-wider text-muted-foreground font-mono">
            {{ t('course_detail.syllabus_summary') }}
          </h3>
          <dl class="space-y-3 text-[13px]">
            <div v-if="course.duration_weeks" class="flex justify-between">
              <dt class="text-muted-foreground">
                {{ t('course_detail.duration') }}
              </dt>
              <dd class="font-mono font-medium">
                {{ course.duration_weeks }} {{ t('course_detail.weeks') }}
              </dd>
            </div>
            <div v-if="course.estimated_hours" class="flex justify-between">
              <dt class="text-muted-foreground">
                {{ t('course_detail.estimated_hours') }}
              </dt>
              <dd class="font-mono font-medium">
                {{ course.estimated_hours }} {{ t('course_detail.hours') }}
              </dd>
            </div>
            <div v-if="course.level" class="flex justify-between">
              <dt class="text-muted-foreground">
                {{ t('course_detail.level') }}
              </dt>
              <dd class="font-medium">
                {{ t(`courses.level_${course.level}`) }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-muted-foreground">
                {{ t('course_detail.language') }}
              </dt>
              <dd class="font-mono font-medium uppercase">
                {{ course.language }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-muted-foreground">
                {{ t('course_detail.lessons') }}
              </dt>
              <dd class="font-mono font-medium">
                {{ flatLessons.length }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-muted-foreground">
                {{ t('course_detail.modules_count') }}
              </dt>
              <dd class="font-mono font-medium">
                {{ modules.length }}
              </dd>
            </div>
          </dl>
        </UiCard>
      </aside>
    </div>

    <!-- Phase 18.2 — O'qituvchi tab -->
    <div v-else-if="activeTab === 'teacher'" class="space-y-4">
      <UiCard v-if="teacher" class="p-6">
        <div class="flex items-start gap-5">
          <!-- Avatar -->
          <div class="shrink-0">
            <img
              v-if="teacher.avatar_url"
              :src="teacher.avatar_url"
              :alt="teacher.full_name"
              class="w-24 h-24 rounded-full object-cover border-2 border-border"
            />
            <div
              v-else
              class="w-24 h-24 rounded-full bg-foreground text-background grid place-items-center text-[28px] font-semibold"
            >
              {{ teacher.full_name.split(' ').slice(0, 2).map((p) => p[0]?.toUpperCase()).join('') }}
            </div>
          </div>

          <div class="flex-1 min-w-0">
            <div class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground mb-1">
              {{ t('course_detail.teacher_label') }}
            </div>
            <h2 class="text-[22px] font-semibold mb-2">{{ teacher.full_name }}</h2>

            <div class="flex flex-wrap gap-2 mb-4">
              <UiBadge variant="default">
                📚 {{ t('course_detail.teacher_courses_count', { n: teacher.courses_count }) }}
              </UiBadge>
            </div>

            <div v-if="teacher.bio" class="text-[14px] leading-relaxed whitespace-pre-line">
              {{ teacher.bio }}
            </div>
            <p v-else class="text-[13px] text-muted-foreground italic">
              {{ t('course_detail.teacher_bio_empty') }}
            </p>
          </div>
        </div>
      </UiCard>
      <UiCard v-else class="p-8 text-center text-muted-foreground">
        {{ t('course_detail.teacher_unknown') }}
      </UiCard>
    </div>

    <!-- Phase 13.14 + 18.8 — Forum tab: oxirgi 3 mavzu preview -->
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

      <UiCard v-if="forumLoading" class="p-6 text-center text-muted-foreground text-[13px]">
        {{ t('common.loading') }}
      </UiCard>

      <UiCard
        v-else-if="forumThreads.length === 0"
        class="p-6 text-center text-muted-foreground text-[13px]"
      >
        {{ t('forum.empty_threads') }}
      </UiCard>

      <ul v-else class="space-y-2">
        <li v-for="th in forumThreads" :key="th.id">
          <button
            type="button"
            class="w-full text-left bg-card border border-border rounded-lg px-5 py-4 hover:border-primary-300 hover:bg-muted/30 transition-colors"
            @click="router.push({ name: 'forum-thread', params: { courseId, threadId: th.id } })"
          >
            <div class="flex items-start gap-3">
              <span class="text-[20px] shrink-0">
                {{ th.is_announcement ? '📢' : th.is_pinned ? '📌' : '💬' }}
              </span>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <UiBadge v-if="th.is_announcement" variant="info">
                    {{ t('forum.announcement') }}
                  </UiBadge>
                  <UiBadge v-if="th.is_pinned" variant="warning">
                    {{ t('forum.pinned') }}
                  </UiBadge>
                  <UiBadge v-if="th.is_locked" variant="danger">
                    {{ t('forum.locked') }}
                  </UiBadge>
                </div>
                <h3 class="text-[14px] font-semibold mb-1 truncate">{{ th.title }}</h3>
                <p
                  v-if="th.body"
                  class="text-[12px] text-muted-foreground line-clamp-2 mb-2"
                >
                  {{ th.body }}
                </p>
                <div class="flex items-center gap-4 text-[11px] text-muted-foreground">
                  <span>{{ th.author_name || t('comments.anonymous', { id: th.author_id ?? '?' }) }}</span>
                  <span>· {{ t('forum.posts_count', { n: th.post_count }) }}</span>
                  <span>· {{ t('forum.views_count', { n: th.view_count }) }}</span>
                  <span class="ml-auto font-mono">{{ fmtRelativeDate(th.last_reply_at ?? th.created_at) }}</span>
                </div>
              </div>
            </div>
          </button>
        </li>
      </ul>
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
