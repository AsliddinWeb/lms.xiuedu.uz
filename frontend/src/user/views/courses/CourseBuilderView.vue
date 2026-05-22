<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiTabs from '@shared/components/ui/UiTabs.vue'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { assignmentsApi } from '@shared/api/assignments'
import {
  coursesApi,
  enrollmentsApi,
  lessonsApi,
  modulesApi,
} from '@shared/api/courses'
import { examsApi, questionsApi } from '@shared/api/exams'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { Assignment } from '@shared/types/assignments'
import type {
  Course,
  CourseStatus,
  EnrollmentStudent,
  Lesson,
  Module,
} from '@shared/types/courses'
import type { Exam, QuestionPublic } from '@shared/types/exams'

import AssignmentDrawer from '@user/components/courses/AssignmentDrawer.vue'
import CourseDrawer from '@user/components/courses/CourseDrawer.vue'
import ExamDrawer from '@user/components/courses/ExamDrawer.vue'
import LessonDrawer from '@user/components/courses/LessonDrawer.vue'
import ModuleDrawer from '@user/components/courses/ModuleDrawer.vue'
import QuestionDrawer from '@user/components/courses/QuestionDrawer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

type Tab = 'structure' | 'students' | 'assignments' | 'exams' | 'settings'

const courseId = computed(() => Number(route.params.id))
const course = ref<Course | null>(null)
const modules = ref<Module[]>([])
const lessonsByModule = ref<Record<number, Lesson[]>>({})
const students = ref<EnrollmentStudent[]>([])

const tab = ref<Tab>('structure')
const loading = ref(false)
const error = ref<string | null>(null)

// Drawer states
const courseDrawerOpen = ref(false)
const moduleDrawerOpen = ref(false)
const editingModule = ref<Module | null>(null)
const lessonDrawerOpen = ref(false)
const lessonModuleId = ref<number | null>(null)
const editingLesson = ref<Lesson | null>(null)
const assignmentDrawerOpen = ref(false)
const editingAssignment = ref<Assignment | null>(null)
const examDrawerOpen = ref(false)
const editingExam = ref<Exam | null>(null)
const questionDrawerOpen = ref(false)
const editingQuestion = ref<QuestionPublic | null>(null)
const questionExamId = ref<number | null>(null)

// Assignments tab
const assignments = ref<Assignment[]>([])

// Exams tab
const exams = ref<Exam[]>([])
const examQuestions = ref<Record<number, QuestionPublic[]>>({})
const expandedExamId = ref<number | null>(null)

const totalLessons = computed(() =>
  Object.values(lessonsByModule.value).reduce((acc, arr) => acc + arr.length, 0),
)

async function loadCourse() {
  loading.value = true
  error.value = null
  try {
    course.value = await coursesApi.get(courseId.value)
    await loadModules()
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'my-courses' })
      return
    }
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function loadModules() {
  modules.value = await modulesApi.list(courseId.value)
  const byId: Record<number, Lesson[]> = {}
  await Promise.all(
    modules.value.map(async (m) => {
      byId[m.id] = await lessonsApi.list(m.id)
    }),
  )
  lessonsByModule.value = byId
}

async function loadStudents() {
  if (!course.value) return
  try {
    const data = await enrollmentsApi.listStudents(courseId.value, { page_size: 200 })
    students.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

async function loadAssignments() {
  if (!course.value) return
  try {
    const data = await assignmentsApi.list({
      course_id: courseId.value,
      page_size: 100,
    })
    assignments.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

async function loadExams() {
  if (!course.value) return
  try {
    const data = await examsApi.list({
      course_id: courseId.value,
      page_size: 100,
    })
    exams.value = data.items
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

async function loadExamQuestions(examId: number) {
  try {
    examQuestions.value = {
      ...examQuestions.value,
      [examId]: await questionsApi.list(examId),
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

watch(tab, (newTab) => {
  if (newTab === 'students') loadStudents()
  if (newTab === 'assignments') loadAssignments()
  if (newTab === 'exams') loadExams()
})

onMounted(loadCourse)

// ---------- Course actions ----------
async function handlePublishToggle() {
  if (!course.value) return
  try {
    course.value =
      course.value.status === 'published'
        ? await coursesApi.unpublish(course.value.id)
        : await coursesApi.publish(course.value.id)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

async function handleCourseSaved(updated: Course) {
  course.value = updated
}

// ---------- Module actions ----------
function openModuleCreate() {
  editingModule.value = null
  moduleDrawerOpen.value = true
}
function openModuleEdit(m: Module) {
  editingModule.value = m
  moduleDrawerOpen.value = true
}
async function handleModuleSaved() {
  await loadModules()
}
async function handleModuleDelete(m: Module) {
  const ok = await confirm({
    title: t('builder.module_delete_confirm'),
    description: m.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await modulesApi.remove(m.id)
    await loadModules()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}
async function moveModule(idx: number, dir: -1 | 1) {
  const next = idx + dir
  if (next < 0 || next >= modules.value.length) return
  const ids = modules.value.map((m) => m.id)
  ;[ids[idx], ids[next]] = [ids[next], ids[idx]]
  try {
    await modulesApi.reorder(courseId.value, ids)
    await loadModules()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

// ---------- Lesson actions ----------
function openLessonCreate(moduleId: number) {
  lessonModuleId.value = moduleId
  editingLesson.value = null
  lessonDrawerOpen.value = true
}
function openLessonEdit(l: Lesson) {
  lessonModuleId.value = l.module_id
  editingLesson.value = l
  lessonDrawerOpen.value = true
}
async function handleLessonSaved() {
  await loadModules()
}
async function handleLessonDelete(l: Lesson) {
  const ok = await confirm({
    title: t('builder.lesson_delete_confirm'),
    description: l.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await lessonsApi.remove(l.id)
    await loadModules()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}
async function moveLesson(moduleId: number, idx: number, dir: -1 | 1) {
  const lessons = lessonsByModule.value[moduleId] ?? []
  const next = idx + dir
  if (next < 0 || next >= lessons.length) return
  const ids = lessons.map((l) => l.id)
  ;[ids[idx], ids[next]] = [ids[next], ids[idx]]
  try {
    await lessonsApi.reorder(moduleId, ids)
    await loadModules()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

// ---------- Assignments ----------
function openAssignmentCreate() {
  editingAssignment.value = null
  assignmentDrawerOpen.value = true
}
function openAssignmentEdit(a: Assignment) {
  editingAssignment.value = a
  assignmentDrawerOpen.value = true
}
async function handleAssignmentDelete(a: Assignment) {
  const ok = await confirm({
    title: t('teacher_assignments.delete_confirm'),
    description: a.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await assignmentsApi.remove(a.id)
    await loadAssignments()
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}
async function handleAssignmentTogglePublish(a: Assignment) {
  try {
    await assignmentsApi.setPublished(a.id, !a.is_published)
    await loadAssignments()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}
function openGradingForAssignment(a: Assignment) {
  router.push({ name: 'grading-inbox', query: { assignment_id: String(a.id) } })
}

// ---------- Exams ----------
function openExamCreate() {
  editingExam.value = null
  examDrawerOpen.value = true
}
function openExamEdit(e: Exam) {
  editingExam.value = e
  examDrawerOpen.value = true
}
async function handleExamSaved() {
  await loadExams()
  if (expandedExamId.value !== null) {
    await loadExamQuestions(expandedExamId.value)
  }
}
async function handleExamDelete(e: Exam) {
  const ok = await confirm({
    title: t('exams.delete_confirm'),
    description: e.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await examsApi.remove(e.id)
    await loadExams()
    toast.success(t('common.deleted'))
  } catch (err) {
    const msg = extractErrorMessage(err, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}
async function handleExamPublish(e: Exam) {
  try {
    await examsApi.publish(e.id)
    await loadExams()
  } catch (err) {
    error.value = extractErrorMessage(err, t('common.save_error'))
  }
}
async function handleExamArchive(e: Exam) {
  const ok = await confirm({
    title: t('exams.archive_confirm'),
    description: e.title,
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await examsApi.archive(e.id)
    await loadExams()
    toast.success(t('common.saved'))
  } catch (err) {
    const msg = extractErrorMessage(err, t('common.save_error'))
    error.value = msg
    toast.error(msg)
  }
}
async function toggleExamExpand(e: Exam) {
  if (expandedExamId.value === e.id) {
    expandedExamId.value = null
    return
  }
  expandedExamId.value = e.id
  if (!examQuestions.value[e.id]) {
    await loadExamQuestions(e.id)
  }
}

function openQuestionCreate(examId: number) {
  questionExamId.value = examId
  editingQuestion.value = null
  questionDrawerOpen.value = true
}
function openQuestionEdit(examId: number, q: QuestionPublic) {
  questionExamId.value = examId
  editingQuestion.value = q
  questionDrawerOpen.value = true
}
async function handleQuestionSaved() {
  if (questionExamId.value !== null) {
    await loadExamQuestions(questionExamId.value)
    await loadExams()
  }
}
async function handleQuestionDelete(examId: number, q: QuestionPublic) {
  const ok = await confirm({
    title: t('exams.question_delete_confirm'),
    description: q.title,
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    await questionsApi.remove(q.id)
    await loadExamQuestions(examId)
    await loadExams()
    toast.success(t('common.deleted'))
  } catch (err) {
    const msg = extractErrorMessage(err, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}
async function moveQuestion(examId: number, idx: number, dir: -1 | 1) {
  const qs = examQuestions.value[examId] ?? []
  const next = idx + dir
  if (next < 0 || next >= qs.length) return
  const ids = qs.map((q) => q.id)
  ;[ids[idx], ids[next]] = [ids[next], ids[idx]]
  try {
    await questionsApi.reorder(examId, ids)
    await loadExamQuestions(examId)
  } catch (err) {
    error.value = extractErrorMessage(err, t('common.save_error'))
  }
}

// ---------- Students ----------
async function handleStudentRemove(s: EnrollmentStudent) {
  const ok = await confirm({
    title: t('students.remove_confirm'),
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

function statusVariant(s: CourseStatus): 'default' | 'success' | 'warning' {
  if (s === 'published') return 'success'
  if (s === 'archived') return 'warning'
  return 'default'
}
</script>

<template>
  <div v-if="loading && !course" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !course" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="course">
    <UiBreadcrumb
      :items="[t('dashboard.crumb_home'), t('courses.title'), course.title]"
      class="mb-6"
    />

    <!-- Header -->
    <div class="mb-6">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-2 flex-wrap">
            <span class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              /{{ course.slug }}
            </span>
            <UiBadge :variant="statusVariant(course.status)" with-dot>
              {{ t(`courses.status_${course.status}`) }}
            </UiBadge>
          </div>
          <h1 class="page-title mb-1.5 truncate">{{ course.title }}</h1>
          <p v-if="course.description" class="page-subtitle line-clamp-2">
            {{ course.description }}
          </p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <UiButton
            v-if="course.status !== 'published'"
            variant="outline"
            @click="courseDrawerOpen = true"
          >
            {{ t('courses.edit') }}
          </UiButton>
          <UiButton v-if="auth.hasPermission('course.publish')" @click="handlePublishToggle">
            {{ course.status === 'published' ? t('courses.unpublish') : t('courses.publish') }}
          </UiButton>
        </div>
      </div>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <!-- Tabs -->
    <UiTabs
      v-model="tab"
      :tabs="[
        { id: 'structure', label: t('courses.tab_structure') },
        { id: 'assignments', label: t('teacher_assignments.tab_assignments') },
        { id: 'exams', label: t('exams.tab_exams') },
        { id: 'students', label: t('courses.tab_students') },
        { id: 'settings', label: t('courses.tab_settings') },
      ]"
    />

    <!-- Structure tab -->
    <div v-if="tab === 'structure'">
      <div class="flex items-center justify-between mb-4">
        <div class="text-[13px] text-muted-foreground">
          {{ t('courses.card_modules', { n: modules.length }) }} ·
          {{ t('courses.card_lessons', { n: totalLessons }) }}
        </div>
        <UiButton
          v-if="course.status !== 'published'"
          size="sm"
          @click="openModuleCreate"
        >
          + {{ t('builder.add_module') }}
        </UiButton>
      </div>

      <div v-if="modules.length === 0" class="text-center py-12 text-muted-foreground">
        {{ t('builder.no_modules') }}
      </div>

      <div v-else class="space-y-3">
        <UiCard
          v-for="(m, mIdx) in modules"
          :key="m.id"
          no-padding
        >
          <div class="p-4 border-b border-border flex items-center gap-3">
            <span class="font-mono text-[11px] text-muted-foreground w-7 shrink-0">
              {{ mIdx + 1 }}.
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-[14px] font-semibold text-foreground truncate">{{ m.title }}</div>
              <div v-if="m.description" class="text-[12px] text-muted-foreground line-clamp-1 mt-0.5">
                {{ m.description }}
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <button
                type="button"
                class="w-7 h-7 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                :disabled="mIdx === 0 || course.status === 'published'"
                :title="t('builder.move_up')"
                @click="moveModule(mIdx, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="w-7 h-7 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                :disabled="mIdx === modules.length - 1 || course.status === 'published'"
                :title="t('builder.move_down')"
                @click="moveModule(mIdx, 1)"
              >
                ↓
              </button>
              <UiButton
                v-if="course.status !== 'published'"
                variant="ghost"
                size="sm"
                @click="openModuleEdit(m)"
              >
                {{ t('common.edit') }}
              </UiButton>
              <UiButton
                v-if="course.status !== 'published'"
                variant="ghost"
                size="sm"
                class="text-danger-600"
                @click="handleModuleDelete(m)"
              >
                {{ t('common.delete') }}
              </UiButton>
            </div>
          </div>

          <!-- Lessons -->
          <div class="divide-y divide-border">
            <div
              v-for="(l, lIdx) in lessonsByModule[m.id] ?? []"
              :key="l.id"
              class="px-4 py-2.5 flex items-center gap-3 hover:bg-muted/30"
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
                    {{ t('builder.no_content_attached') }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  class="w-7 h-7 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                  :disabled="lIdx === 0 || course.status === 'published'"
                  @click="moveLesson(m.id, lIdx, -1)"
                >
                  ↑
                </button>
                <button
                  type="button"
                  class="w-7 h-7 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                  :disabled="lIdx === (lessonsByModule[m.id]?.length ?? 0) - 1 || course.status === 'published'"
                  @click="moveLesson(m.id, lIdx, 1)"
                >
                  ↓
                </button>
                <UiButton
                  v-if="course.status !== 'published'"
                  variant="ghost"
                  size="sm"
                  @click="openLessonEdit(l)"
                >
                  {{ t('common.edit') }}
                </UiButton>
                <UiButton
                  v-if="course.status !== 'published'"
                  variant="ghost"
                  size="sm"
                  class="text-danger-600"
                  @click="handleLessonDelete(l)"
                >
                  {{ t('common.delete') }}
                </UiButton>
              </div>
            </div>
            <div v-if="course.status !== 'published'" class="p-2.5">
              <UiButton variant="ghost" size="sm" @click="openLessonCreate(m.id)">
                + {{ t('builder.add_lesson') }}
              </UiButton>
            </div>
          </div>
        </UiCard>
      </div>
    </div>

    <!-- Students tab -->
    <div v-else-if="tab === 'students'">
      <UiCard no-padding>
        <div v-if="students.length === 0" class="p-8 text-center text-muted-foreground">
          {{ t('students.empty') }}
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
                  @click="handleStudentRemove(s)"
                >
                  {{ t('common.delete') }}
                </UiButton>
              </td>
            </tr>
          </tbody>
        </table>
      </UiCard>
    </div>

    <!-- Assignments tab -->
    <div v-else-if="tab === 'assignments'">
      <div class="flex items-center justify-between mb-4">
        <div class="text-[13px] text-muted-foreground">
          {{ assignments.length }} {{ t('teacher_assignments.tab_assignments') }}
        </div>
        <UiButton size="sm" @click="openAssignmentCreate">
          + {{ t('teacher_assignments.add_assignment') }}
        </UiButton>
      </div>

      <div
        v-if="assignments.length === 0"
        class="text-center py-12 text-muted-foreground"
      >
        {{ t('teacher_assignments.no_assignments') }}
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <UiCard v-for="a in assignments" :key="a.id">
          <template #header>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <UiBadge variant="default">
                  {{ t(`assignments.type_${a.type}`) }}
                </UiBadge>
                <UiBadge :variant="a.is_published ? 'success' : 'default'" with-dot>
                  {{
                    a.is_published
                      ? t('courses.status_published')
                      : t('courses.status_draft')
                  }}
                </UiBadge>
              </div>
              <h3 class="text-base font-semibold text-foreground truncate">
                {{ a.title }}
              </h3>
              <div class="font-mono text-[11px] text-muted-foreground mt-0.5">
                due: {{ a.due_date.slice(0, 16).replace('T', ' ') }}
              </div>
            </div>
          </template>

          <p
            v-if="a.description"
            class="text-[13px] text-muted-foreground line-clamp-2 mb-2"
          >
            {{ a.description }}
          </p>

          <div class="flex flex-wrap gap-3 text-[11px] font-mono text-muted-foreground">
            <span>max: {{ a.max_score }}</span>
            <span>attempts: {{ a.max_attempts }}</span>
            <span v-if="Number(a.late_penalty_per_day) > 0">
              -{{ a.late_penalty_per_day }}%/day
            </span>
          </div>

          <template #actions>
            <div class="flex flex-wrap gap-1.5">
              <UiButton size="sm" @click="openGradingForAssignment(a)">
                {{ t('teacher_assignments.open_grading') }}
              </UiButton>
              <UiButton variant="outline" size="sm" @click="openAssignmentEdit(a)">
                {{ t('common.edit') }}
              </UiButton>
              <UiButton
                variant="ghost"
                size="sm"
                @click="handleAssignmentTogglePublish(a)"
              >
                {{
                  a.is_published
                    ? t('teacher_assignments.unpublish')
                    : t('teacher_assignments.publish')
                }}
              </UiButton>
              <UiButton
                variant="ghost"
                size="sm"
                class="text-danger-600"
                @click="handleAssignmentDelete(a)"
              >
                {{ t('common.delete') }}
              </UiButton>
            </div>
          </template>
        </UiCard>
      </div>
    </div>

    <!-- Exams tab -->
    <div v-else-if="tab === 'exams'">
      <div class="flex items-center justify-between mb-4">
        <div class="text-[13px] text-muted-foreground">
          {{ exams.length }} {{ t('exams.tab_exams') }}
        </div>
        <UiButton size="sm" @click="openExamCreate">
          + {{ t('exams.add_exam') }}
        </UiButton>
      </div>

      <div v-if="exams.length === 0" class="text-center py-12 text-muted-foreground">
        {{ t('exams.no_exams') }}
      </div>

      <div v-else class="space-y-3">
        <UiCard v-for="e in exams" :key="e.id" no-padding>
          <div class="p-4 border-b border-border flex items-center gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <UiBadge variant="default">
                  {{ t(`exams.type_${e.type}`) }}
                </UiBadge>
                <UiBadge
                  :variant="
                    e.status === 'published'
                      ? 'success'
                      : e.status === 'archived'
                        ? 'warning'
                        : 'default'
                  "
                  with-dot
                >
                  {{ t(`exams.status_${e.status}`) }}
                </UiBadge>
                <UiBadge v-if="e.proctoring_enabled" variant="default">
                  {{ t('exams.proctoring_on') }}
                </UiBadge>
              </div>
              <div class="text-[14px] font-semibold text-foreground truncate">
                {{ e.title }}
              </div>
              <div class="flex flex-wrap gap-3 text-[11px] font-mono text-muted-foreground mt-1">
                <span>{{ e.duration_minutes }} min</span>
                <span>{{ e.total_questions }} q</span>
                <span>{{ e.total_points }} pts</span>
                <span>pass: {{ e.passing_score }}%</span>
                <span>attempts: {{ e.max_attempts }}</span>
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <UiButton variant="ghost" size="sm" @click="toggleExamExpand(e)">
                {{
                  expandedExamId === e.id
                    ? t('exams.collapse_questions')
                    : t('exams.expand_questions')
                }}
              </UiButton>
              <UiButton
                v-if="e.status !== 'draft'"
                variant="ghost"
                size="sm"
                @click="router.push({ name: 'exam-attempts', params: { id: e.id } })"
              >
                {{ t('exams.view_attempts') }}
              </UiButton>
              <UiButton
                v-if="e.status === 'draft'"
                variant="outline"
                size="sm"
                @click="handleExamPublish(e)"
              >
                {{ t('exams.publish') }}
              </UiButton>
              <UiButton
                v-else-if="e.status === 'published'"
                variant="ghost"
                size="sm"
                @click="handleExamArchive(e)"
              >
                {{ t('exams.archive') }}
              </UiButton>
              <UiButton
                v-if="e.status !== 'archived'"
                variant="ghost"
                size="sm"
                @click="openExamEdit(e)"
              >
                {{ t('common.edit') }}
              </UiButton>
              <UiButton
                v-if="e.status !== 'published'"
                variant="ghost"
                size="sm"
                class="text-danger-600"
                @click="handleExamDelete(e)"
              >
                {{ t('common.delete') }}
              </UiButton>
            </div>
          </div>

          <!-- Questions -->
          <div v-if="expandedExamId === e.id" class="divide-y divide-border">
            <div
              v-for="(q, qIdx) in examQuestions[e.id] ?? []"
              :key="q.id"
              class="px-4 py-2.5 flex items-center gap-3 hover:bg-muted/30"
            >
              <span class="font-mono text-[11px] text-muted-foreground w-7 shrink-0">
                {{ qIdx + 1 }}.
              </span>
              <UiBadge variant="default" class="shrink-0">
                {{ t(`exams.qtype_${q.type}`) }}
              </UiBadge>
              <div class="flex-1 min-w-0">
                <div class="text-[13px] font-medium text-foreground line-clamp-1">
                  {{ q.title }}
                </div>
                <div class="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5 font-mono">
                  <span>{{ q.points }} pts</span>
                  <span v-if="!q.required" class="italic">{{ t('common.optional') }}</span>
                </div>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  class="w-7 h-7 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                  :disabled="qIdx === 0 || e.status === 'published'"
                  @click="moveQuestion(e.id, qIdx, -1)"
                >
                  ↑
                </button>
                <button
                  type="button"
                  class="w-7 h-7 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                  :disabled="qIdx === (examQuestions[e.id]?.length ?? 0) - 1 || e.status === 'published'"
                  @click="moveQuestion(e.id, qIdx, 1)"
                >
                  ↓
                </button>
                <UiButton
                  v-if="e.status !== 'published'"
                  variant="ghost"
                  size="sm"
                  @click="openQuestionEdit(e.id, q)"
                >
                  {{ t('common.edit') }}
                </UiButton>
                <UiButton
                  v-if="e.status !== 'published'"
                  variant="ghost"
                  size="sm"
                  class="text-danger-600"
                  @click="handleQuestionDelete(e.id, q)"
                >
                  {{ t('common.delete') }}
                </UiButton>
              </div>
            </div>
            <div
              v-if="(examQuestions[e.id]?.length ?? 0) === 0"
              class="px-4 py-6 text-center text-[13px] text-muted-foreground"
            >
              {{ t('exams.no_questions') }}
            </div>
            <div v-if="e.status !== 'published'" class="p-2.5">
              <UiButton variant="ghost" size="sm" @click="openQuestionCreate(e.id)">
                + {{ t('exams.add_question') }}
              </UiButton>
            </div>
          </div>
        </UiCard>
      </div>
    </div>

    <!-- Settings tab -->
    <div v-else-if="tab === 'settings'">
      <UiCard>
        <dl class="text-[13px] space-y-2">
          <div class="flex justify-between">
            <dt class="text-muted-foreground">{{ t('courses.field_type') }}</dt>
            <dd>{{ t(`courses.type_${course.type}`) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-muted-foreground">{{ t('courses.field_enrollment_type') }}</dt>
            <dd>{{ t(`courses.enrollment_${course.enrollment_type}`) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-muted-foreground">{{ t('courses.field_language') }}</dt>
            <dd class="font-mono">{{ course.language }}</dd>
          </div>
          <div v-if="course.duration_weeks" class="flex justify-between">
            <dt class="text-muted-foreground">{{ t('courses.field_duration_weeks') }}</dt>
            <dd>{{ course.duration_weeks }}</dd>
          </div>
          <div v-if="course.estimated_hours" class="flex justify-between">
            <dt class="text-muted-foreground">{{ t('courses.field_estimated_hours') }}</dt>
            <dd>{{ course.estimated_hours }}</dd>
          </div>
          <div v-if="course.max_students" class="flex justify-between">
            <dt class="text-muted-foreground">{{ t('courses.field_max_students') }}</dt>
            <dd>{{ course.max_students }}</dd>
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

    <!-- Drawers -->
    <CourseDrawer
      :open="courseDrawerOpen"
      :course="course"
      @close="courseDrawerOpen = false"
      @saved="handleCourseSaved"
    />
    <ModuleDrawer
      :open="moduleDrawerOpen"
      :course-id="courseId"
      :module="editingModule"
      @close="moduleDrawerOpen = false"
      @saved="handleModuleSaved"
    />
    <LessonDrawer
      v-if="lessonModuleId !== null"
      :open="lessonDrawerOpen"
      :module-id="lessonModuleId"
      :lesson="editingLesson"
      @close="lessonDrawerOpen = false"
      @saved="handleLessonSaved"
    />
    <AssignmentDrawer
      :open="assignmentDrawerOpen"
      :course-id="courseId"
      :assignment="editingAssignment"
      @close="assignmentDrawerOpen = false"
      @saved="loadAssignments"
    />
    <ExamDrawer
      :open="examDrawerOpen"
      :course-id="courseId"
      :exam="editingExam"
      @close="examDrawerOpen = false"
      @saved="handleExamSaved"
    />
    <QuestionDrawer
      v-if="questionExamId !== null"
      :open="questionDrawerOpen"
      :exam-id="questionExamId"
      :question="editingQuestion"
      @close="questionDrawerOpen = false"
      @saved="handleQuestionSaved"
    />
  </template>
</template>
