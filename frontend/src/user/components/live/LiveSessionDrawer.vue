<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { coursesApi, lessonsApi, modulesApi } from '@shared/api/courses'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'
import type { Course, Lesson, Module } from '@shared/types/courses'
import type {
  LiveProvider,
  LiveSession,
  LiveSessionCreatePayload,
} from '@shared/types/live'

interface Props {
  open: boolean
  session?: LiveSession | null
}
const props = withDefaults(defineProps<Props>(), { session: null })
const emit = defineEmits<{ close: []; saved: [session: LiveSession] }>()

const { t } = useI18n()

const title = ref('')
const description = ref('')
const courseId = ref<number | null>(null)
const lessonId = ref<number | null>(null)
const scheduledStart = ref('')
const scheduledEnd = ref('')
const durationMinutes = ref<number>(60)
const provider = ref<LiveProvider>('native')
const isRecordingEnabled = ref(false)
const minAttendancePercent = ref<number>(75)
const requiresApproval = ref<boolean>(false)

const courses = ref<Course[]>([])
const modules = ref<Module[]>([])
const lessons = ref<Lesson[]>([])

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const courseOptions = computed(() => [
  { value: null as number | null, label: t('live.field_course_none') },
  ...courses.value.map((c) => ({ value: c.id, label: c.title })),
])

const lessonOptions = computed(() => {
  const out: Array<{ value: number | null; label: string }> = [
    { value: null, label: t('live.field_lesson_none') },
  ]
  for (const m of modules.value) {
    const ls = lessons.value.filter((l) => l.module_id === m.id)
    for (const l of ls) {
      out.push({ value: l.id, label: `${m.title} → ${l.title}` })
    }
  }
  return out
})

// Zoom yagona provider — picker olib tashlandi.

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  const tzOffsetMs = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tzOffsetMs).toISOString().slice(0, 16)
}

function fromLocalInput(local: string): string {
  // datetime-local → ISO with timezone (browser local)
  return new Date(local).toISOString()
}

async function loadCourseStructure(cid: number | null) {
  if (cid == null) {
    modules.value = []
    lessons.value = []
    return
  }
  modules.value = await modulesApi.list(cid)
  const all: Lesson[] = []
  for (const m of modules.value) {
    const ls = await lessonsApi.list(m.id)
    all.push(...ls)
  }
  lessons.value = all
}

watch(courseId, async (cid) => {
  await loadCourseStructure(cid)
  // Agar yangi course tanlansa va eski lesson moduliga tegishli bo'lmasa — reset
  if (lessonId.value && !lessons.value.some((l) => l.id === lessonId.value)) {
    lessonId.value = null
  }
})

watch(
  () => [props.open, props.session],
  async () => {
    errorMsg.value = null
    if (!props.open) return
    // load courses (host'ning yaratgan kurslari — backend filter qiladi)
    try {
      const data = await coursesApi.list({ page_size: 100 })
      courses.value = data.items
    } catch {
      courses.value = []
    }

    if (props.session) {
      const s = props.session
      title.value = s.title
      description.value = s.description ?? ''
      courseId.value = s.course_id
      await loadCourseStructure(s.course_id)
      lessonId.value = s.lesson_id
      scheduledStart.value = toLocalInput(s.scheduled_start)
      scheduledEnd.value = toLocalInput(s.scheduled_end)
      durationMinutes.value = s.duration_minutes
      provider.value = s.provider
      isRecordingEnabled.value = s.is_recording_enabled
      minAttendancePercent.value = s.min_attendance_percent
      requiresApproval.value = s.requires_approval ?? false
    } else {
      title.value = ''
      description.value = ''
      courseId.value = null
      lessonId.value = null
      modules.value = []
      lessons.value = []
      scheduledStart.value = toLocalInput(
        new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      )
      scheduledEnd.value = toLocalInput(
        new Date(Date.now() + 90 * 60 * 1000).toISOString(),
      )
      durationMinutes.value = 60
      provider.value = 'native'
      isRecordingEnabled.value = false
      minAttendancePercent.value = 75
      requiresApproval.value = false
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  errorMsg.value = null
  if (!title.value.trim()) {
    errorMsg.value = t('live.error_title_required')
    return
  }
  if (!scheduledStart.value || !scheduledEnd.value) {
    errorMsg.value = t('live.error_dates_required')
    return
  }

  const startIso = fromLocalInput(scheduledStart.value)
  const endIso = fromLocalInput(scheduledEnd.value)
  if (new Date(endIso) <= new Date(startIso)) {
    errorMsg.value = t('live.error_end_before_start')
    return
  }

  submitting.value = true
  try {
    const payload: LiveSessionCreatePayload = {
      title: title.value.trim(),
      description: description.value.trim() || null,
      course_id: courseId.value,
      lesson_id: lessonId.value,
      scheduled_start: startIso,
      scheduled_end: endIso,
      duration_minutes: durationMinutes.value,
      provider: provider.value,
      is_recording_enabled: isRecordingEnabled.value,
      min_attendance_percent: minAttendancePercent.value,
      requires_approval: requiresApproval.value,
    }
    const saved = props.session
      ? await liveSessionsApi.update(props.session.id, payload)
      : await liveSessionsApi.create(payload)
    emit('saved', saved)
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save') + ' xato')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="session ? t('live.drawer_edit') : t('live.drawer_create')"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="live-form" @submit.prevent="handleSubmit">
      <UiFormField :label="t('live.field_title')" required>
        <UiInput v-model="title" required maxlength="500" />
      </UiFormField>

      <UiFormField :label="t('live.field_description')">
        <textarea
          v-model="description"
          rows="2"
          class="rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus w-full"
        ></textarea>
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('live.field_course')">
          <UiSelect v-model="courseId" :options="courseOptions" />
        </UiFormField>
        <UiFormField :label="t('live.field_lesson')">
          <UiSelect v-model="lessonId" :options="lessonOptions" />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('live.field_start')" required>
          <UiInput v-model="scheduledStart" type="datetime-local" required />
        </UiFormField>
        <UiFormField :label="t('live.field_end')" required>
          <UiInput v-model="scheduledEnd" type="datetime-local" required />
        </UiFormField>
      </div>

      <UiFormField :label="t('live.field_duration')" :hint="t('live.field_duration_hint')">
        <UiInput v-model="durationMinutes" type="number" min="5" max="600" />
      </UiFormField>

      <UiFormField :label="t('live.field_min_attendance')" :hint="t('live.field_min_attendance_hint')">
        <UiInput v-model="minAttendancePercent" type="number" min="0" max="100" />
      </UiFormField>

      <label class="flex items-center gap-2 mt-2 cursor-pointer">
        <input
          v-model="isRecordingEnabled"
          type="checkbox"
          class="w-3.5 h-3.5 accent-foreground"
        />
        <span class="text-[13px]">{{ t('live.field_recording') }}</span>
      </label>

      <label class="flex items-start gap-2 mt-2 mb-4 cursor-pointer">
        <input
          v-model="requiresApproval"
          type="checkbox"
          class="w-3.5 h-3.5 accent-foreground mt-0.5"
        />
        <span>
          <span class="text-[13px]">{{ t('live.field_requires_approval') }}</span>
          <span class="block text-[11px] text-muted-foreground">
            {{ t('live.field_requires_approval_hint') }}
          </span>
        </span>
      </label>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="live-form" :loading="submitting">
          {{ session ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
