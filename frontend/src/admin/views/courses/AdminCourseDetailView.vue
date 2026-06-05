<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '@shared/i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import {
  coursesApi,
  enrollmentsApi,
  lessonsApi,
  modulesApi,
} from '@shared/api/courses'
import { usersApi } from '@shared/api/users'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import type {
  Course,
  CourseStatus,
  EnrollmentStudent,
  Lesson,
  Module,
} from '@shared/types/courses'

import AddStudentDrawer from '@admin/components/courses/AddStudentDrawer.vue'

type Tab = 'overview' | 'students' | 'structure'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const courseId = computed(() => Number(route.params.id))

const course = ref<Course | null>(null)
const author = ref<{ id: number; name: string } | null>(null)
const modules = ref<Module[]>([])
const lessonsByModule = ref<Record<number, Lesson[]>>({})
const students = ref<EnrollmentStudent[]>([])

const tab = ref<Tab>('overview')
const loading = ref(false)
const error = ref<string | null>(null)
const addOpen = ref(false)

const totalLessons = computed(() =>
  Object.values(lessonsByModule.value).reduce((acc, arr) => acc + arr.length, 0),
)

async function loadCourse() {
  loading.value = true
  error.value = null
  try {
    const c = await coursesApi.get(courseId.value)
    course.value = c

    if (c.primary_author_id) {
      try {
        const u = await usersApi.get(c.primary_author_id)
        author.value = { id: u.id, name: u.full_name }
      } catch {
        author.value = { id: c.primary_author_id, name: `#${c.primary_author_id}` }
      }
    }

    await Promise.all([loadStructure(), loadStudents()])
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'admin-courses' })
      return
    }
    error.value = extractErrorMessage(e, 'Yuklashda xato')
  } finally {
    loading.value = false
  }
}

async function loadStructure() {
  modules.value = await modulesApi.list(courseId.value)
  const map: Record<number, Lesson[]> = {}
  await Promise.all(
    modules.value.map(async (m) => {
      map[m.id] = await lessonsApi.list(m.id)
    }),
  )
  lessonsByModule.value = map
}

async function loadStudents() {
  try {
    const data = await enrollmentsApi.listStudents(courseId.value, { page_size: 200 })
    students.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, 'Talabalarni yuklashda xato')
  }
}

onMounted(loadCourse)

watch(courseId, loadCourse)

function statusVariant(s: CourseStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}

async function handleRemoveStudent(s: EnrollmentStudent) {
  const ok = await confirm({
    title: t('admin_courses.remove_student_confirm'),
    description: s.full_name ?? s.email,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await enrollmentsApi.removeStudent(courseId.value, s.user_id)
    await loadStudents()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  try {
    return new Intl.DateTimeFormat(intlLocale(locale.value), {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    }).format(new Date(s))
  } catch {
    return s.slice(0, 10)
  }
}
</script>

<template>
  <div v-if="loading && !course" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !course" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="course">
    <!-- Header -->
    <div class="mb-6">
      <button
        type="button"
        class="text-[12px] font-mono text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1"
        @click="router.push({ name: 'admin-courses' })"
      >
        ← {{ t('admin_courses.back_to_courses') }}
      </button>
      <div class="flex items-end justify-between gap-6">
        <div class="min-w-0">
          <div class="flex items-center gap-2 mb-2">
            <div class="mono-tag">{{ course.slug }}</div>
            <UiBadge :variant="statusVariant(course.status)" with-dot>
              {{ t(`courses.status_${course.status}`) }}
            </UiBadge>
            <UiBadge variant="default">{{ t(`courses.type_${course.type}`) }}</UiBadge>
          </div>
          <h1 class="page-title mb-1.5 truncate">{{ course.title }}</h1>
          <p v-if="course.description" class="page-subtitle line-clamp-2">
            {{ course.description }}
          </p>
        </div>
      </div>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <!-- Stat strip -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
      <UiCard>
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('admin_courses.header_author') }}
        </div>
        <div class="text-[13px] font-medium mt-1 truncate">
          {{ author ? author.name : '—' }}
        </div>
      </UiCard>
      <UiCard>
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('admin_courses.header_modules') }} · {{ t('admin_courses.header_lessons') }}
        </div>
        <div class="text-[13px] font-medium mt-1 font-mono">
          {{ modules.length }} · {{ totalLessons }}
        </div>
      </UiCard>
      <UiCard>
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('admin_courses.header_students') }}
        </div>
        <div class="text-[13px] font-medium mt-1 font-mono">{{ students.length }}</div>
      </UiCard>
    </div>

    <!-- Tabs -->
    <div class="border-b border-border mb-6 flex gap-1">
      <button
        v-for="opt in (['overview', 'students', 'structure'] as Tab[])"
        :key="opt"
        type="button"
        class="px-4 py-2.5 text-[13px] font-medium border-b-2 -mb-px transition-colors"
        :class="
          tab === opt
            ? 'border-foreground text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        "
        @click="tab = opt"
      >
        {{ t(`admin_courses.tab_${opt}`) }}
      </button>
    </div>

    <!-- Overview -->
    <div v-if="tab === 'overview'">
      <UiCard>
        <dl class="text-[13px] grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2.5">
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('courses.field_language') }}</dt>
            <dd class="font-mono">{{ course.language }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('courses.field_enrollment_type') }}</dt>
            <dd>{{ t(`courses.enrollment_${course.enrollment_type}`) }}</dd>
          </div>
          <div v-if="course.duration_weeks" class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('courses.field_duration_weeks') }}</dt>
            <dd>{{ course.duration_weeks }}</dd>
          </div>
          <div v-if="course.estimated_hours" class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('courses.field_estimated_hours') }}</dt>
            <dd>{{ course.estimated_hours }}</dd>
          </div>
          <div v-if="course.max_students" class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('courses.field_max_students') }}</dt>
            <dd class="font-mono">{{ course.max_students }}</dd>
          </div>
          <div v-if="course.level" class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('courses.field_level') }}</dt>
            <dd>{{ t(`courses.level_${course.level}`) }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">created_at</dt>
            <dd class="font-mono">{{ fmtDate(course.created_at) }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">published_at</dt>
            <dd class="font-mono">{{ fmtDate(course.published_at) }}</dd>
          </div>
        </dl>

        <div v-if="course.objectives.length > 0" class="mt-4 pt-4 border-t border-border">
          <div class="mono-tag mb-2">{{ t('courses.field_objectives') }}</div>
          <ul class="text-[13px] space-y-1 list-disc pl-5">
            <li v-for="(o, i) in course.objectives" :key="i">{{ o }}</li>
          </ul>
        </div>

        <div v-if="course.skills_gained.length > 0" class="mt-4 pt-4 border-t border-border">
          <div class="mono-tag mb-2">{{ t('courses.field_skills') }}</div>
          <div class="flex flex-wrap gap-1.5">
            <UiBadge v-for="(s, i) in course.skills_gained" :key="i" variant="default">
              {{ s }}
            </UiBadge>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- Students -->
    <div v-else-if="tab === 'students'">
      <div class="flex items-center justify-end mb-3">
        <UiButton size="sm" @click="addOpen = true">
          + {{ t('admin_courses.add_student') }}
        </UiButton>
      </div>

      <UiCard no-padding>
        <div v-if="students.length === 0" class="p-8 text-center text-muted-foreground">
          {{ t('admin_courses.students_empty') }}
        </div>
        <table v-else class="w-full text-[13px]">
          <thead class="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('students.col_name') }}</th>
              <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('students.col_email') }}</th>
              <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('students.col_method') }}</th>
              <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('students.col_progress') }}</th>
              <th scope="col" class="text-left px-4 py-2.5 font-mono">{{ t('students.col_status') }}</th>
              <th scope="col" class="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="s in students" :key="s.user_id" class="hover:bg-muted/30">
              <td class="px-4 py-3 font-medium">{{ s.full_name }}</td>
              <td class="px-4 py-3 font-mono text-[12px] text-muted-foreground">{{ s.email }}</td>
              <td class="px-4 py-3">
                <UiBadge variant="default">
                  {{ t(`courses.enrollment_${s.enrollment_method}`) }}
                </UiBadge>
              </td>
              <td class="px-4 py-3 font-mono">{{ s.progress_percent }}%</td>
              <td class="px-4 py-3">
                <UiBadge
                  :variant="
                    s.completion_status === 'completed'
                      ? 'success'
                      : s.completion_status === 'failed' || s.completion_status === 'dropped'
                        ? 'warning'
                        : 'default'
                  "
                >
                  {{ t(`students.completion_${s.completion_status}`) }}
                </UiBadge>
              </td>
              <td class="px-4 py-3 text-right">
                <UiButton
                  variant="ghost"
                  size="sm"
                  class="text-danger-600"
                  @click="handleRemoveStudent(s)"
                >
                  {{ t('common.delete') }}
                </UiButton>
              </td>
            </tr>
          </tbody>
        </table>
      </UiCard>
    </div>

    <!-- Structure -->
    <div v-else>
      <div v-if="modules.length === 0" class="text-center py-12 text-muted-foreground">
        {{ t('admin_courses.structure_empty') }}
      </div>
      <div v-else class="space-y-3">
        <UiCard v-for="(m, mIdx) in modules" :key="m.id" no-padding>
          <div class="px-4 py-3 border-b border-border flex items-center gap-3">
            <span class="font-mono text-[11px] text-muted-foreground w-7 shrink-0">
              {{ mIdx + 1 }}.
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-[14px] font-semibold text-foreground truncate">{{ m.title }}</div>
              <div v-if="m.description" class="text-[12px] text-muted-foreground line-clamp-1 mt-0.5">
                {{ m.description }}
              </div>
            </div>
            <span class="font-mono text-[11px] text-muted-foreground shrink-0">
              {{ t('admin_courses.module_lesson_count', { n: (lessonsByModule[m.id] ?? []).length }) }}
            </span>
          </div>
          <div class="divide-y divide-border">
            <div
              v-for="(l, lIdx) in lessonsByModule[m.id] ?? []"
              :key="l.id"
              class="px-4 py-2.5 flex items-center gap-3"
            >
              <span class="font-mono text-[11px] text-muted-foreground w-7 shrink-0">
                {{ mIdx + 1 }}.{{ lIdx + 1 }}
              </span>
              <div class="flex-1 min-w-0">
                <div class="text-[13px] font-medium text-foreground truncate">{{ l.title }}</div>
                <div class="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5">
                  <span v-if="l.estimated_minutes" class="font-mono">{{ l.estimated_minutes }} min</span>
                  <span v-if="!l.is_required_for_completion" class="font-mono italic">
                    {{ t('common.optional') }}
                  </span>
                  <span v-if="l.primary_content_id" class="font-mono">
                    content #{{ l.primary_content_id }}
                  </span>
                  <span v-else class="font-mono italic text-warning-600">
                    {{ t('admin_courses.no_content_attached') }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </UiCard>
      </div>
    </div>

    <AddStudentDrawer
      :open="addOpen"
      :course-id="courseId"
      @close="addOpen = false"
      @added="loadStudents"
    />
  </template>
</template>
