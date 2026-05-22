<script setup lang="ts">
/**
 * Wireframe 05 (Courses List) — talaba "Mening kurslarim" tab.
 * 3-col grid UiCourseCard'lar bilan, har biri real progress ko'rsatadi.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCourseCard from '@shared/components/ui/UiCourseCard.vue'
import UiEmptyState from '@shared/components/ui/UiEmptyState.vue'
import { coursesApi, enrollmentsApi, progressApi } from '@shared/api/courses'
import { certificatesApi } from '@shared/api/certificates'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { useAuthStore } from '@shared/stores/auth'
import type { Course, CourseProgress } from '@shared/types/courses'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

interface Row {
  course: Course
  progress: CourseProgress
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
// Phase 13.23 — course_id => certificate (agar bor bo'lsa)
const certByCourse = ref<Record<number, number>>({})

async function load() {
  if (!auth.user) return
  loading.value = true
  error.value = null
  try {
    const data = await coursesApi.list({
      enrolled_user_id: auth.user.id,
      page_size: 100,
    })
    const courses = data.items
    const progresses = await Promise.all(
      courses.map((c) => progressApi.myCourseProgress(c.id)),
    )
    rows.value = courses.map((course, i) => ({ course, progress: progresses[i] }))
    // Yakunlangan kurslar pastga
    rows.value.sort((a, b) => {
      const av = a.progress.completion_status === 'completed' ? 1 : 0
      const bv = b.progress.completion_status === 'completed' ? 1 : 0
      return av - bv
    })

    // Phase 13.23 — sertifikatlar (background, xato bo'lsa yutamiz)
    try {
      const certs = await certificatesApi.listMine()
      const map: Record<number, number> = {}
      for (const c of certs) {
        if (c.revoked_at === null) map[c.course_id] = c.id
      }
      certByCourse.value = map
    } catch {
      // ignore
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function handleUnenroll(c: Course) {
  const ok = await confirm({
    title: t('learning.unenroll_confirm'),
    description: c.title,
    variant: 'danger',
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await enrollmentsApi.selfUnenroll(c.id)
    await load()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

function open(c: Course) {
  router.push({ name: 'course-detail', params: { id: c.id } })
}

function fmtDate(s: string): string {
  try {
    return new Intl.DateTimeFormat(locale.value, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    }).format(new Date(s))
  } catch {
    return s.slice(0, 10)
  }
}

function courseCategory(c: Course): string {
  const parts: string[] = []
  if (c.type) parts.push(t(`courses.type_${c.type}`))
  if (c.level) parts.push(t(`courses.level_${c.level}`))
  return parts.join(' · ')
}
</script>

<template>
  <!-- PAGE HEADER -->
  <div class="mb-6">
    <UiBreadcrumb :items="[t('dashboard.crumb_home'), t('learning.title')]" />
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('learning.title') }}</h1>
        <p class="page-subtitle">{{ t('learning.subtitle') }}</p>
      </div>
    </div>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && rows.length === 0" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <!-- Empty state — UiEmptyState (Phase 13.26) -->
  <UiEmptyState
    v-else-if="rows.length === 0"
    :title="t('learning.no_courses')"
    :description="t('learning.no_courses_hint')"
  >
    <template #action>
      <UiButton variant="outline" size="sm" disabled>
        {{ t('learning.browse_catalog') }} (Ph.14)
      </UiButton>
    </template>
  </UiEmptyState>

  <!-- 3-col grid -->
  <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
    <UiCourseCard
      v-for="{ course, progress } in rows"
      :key="course.id"
      :title="course.title"
      :category="courseCategory(course)"
      :cover-url="course.cover_image_url"
      :progress="Number(progress.percent ?? 0)"
      :stats="[
        { icon: '📚', label: `${progress.completed_lessons}/${progress.total_required_lessons}` },
        course.estimated_hours ? { icon: '⏱', label: `${course.estimated_hours}h` } : null,
        { icon: '🌐', label: course.language },
      ].filter((s): s is { icon: string; label: string } => s !== null)"
      @click="open(course)"
    >
      <template #actions>
        <div class="flex items-center justify-between mt-3">
          <div class="flex items-center gap-1.5 flex-wrap">
            <UiBadge
              :variant="progress.completion_status === 'completed' ? 'success' : 'info'"
              with-dot
            >
              {{
                progress.completion_status === 'completed'
                  ? t('learning.completed')
                  : t('learning.in_progress')
              }}
            </UiBadge>
            <!-- Phase 13.23 — sertifikat chip -->
            <UiBadge
              v-if="certByCourse[course.id]"
              variant="default"
              class="cursor-pointer"
              @click.stop="$router.push({ name: 'my-certificates' })"
            >
              ★ {{ t('learning.cert_chip') }}
            </UiBadge>
          </div>

          <div class="flex items-center gap-1.5">
            <UiButton
              size="sm"
              @click.stop="open(course)"
            >
              {{
                progress.completion_status === 'completed'
                  ? t('learning.review')
                  : t('learning.continue')
              }} →
            </UiButton>
            <button
              type="button"
              class="text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-700/15 rounded p-1.5"
              :title="t('learning.unenroll')"
              @click.stop="handleUnenroll(course)"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M3 3l8 8M11 3l-8 8" />
              </svg>
            </button>
          </div>
        </div>

        <div
          v-if="progress.completed_at"
          class="mt-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider"
        >
          ✓ {{ fmtDate(progress.completed_at) }}
        </div>
      </template>
    </UiCourseCard>
  </div>
</template>
