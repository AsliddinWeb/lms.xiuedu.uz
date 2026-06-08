<script setup lang="ts">
/** Talaba detali — pedagog kurslaridagi yozilishlari (progress/baho). */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiProgressBar from '@shared/components/ui/UiProgressBar.vue'
import { enrollmentsApi } from '@shared/api/courses'
import type { StudentCourseItem, TeacherStudent } from '@shared/types/courses'

const props = defineProps<{ open: boolean; student: TeacherStudent | null }>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const courses = ref<StudentCourseItem[]>([])
const loading = ref(false)

watch(
  () => [props.open, props.student?.user_id],
  async () => {
    if (!props.open || !props.student) return
    loading.value = true
    courses.value = []
    try {
      courses.value = await enrollmentsApi.studentCourses(props.student.user_id)
    } catch {
      courses.value = []
    } finally {
      loading.value = false
    }
  },
)

function statusVariant(s: string): 'default' | 'success' | 'warning' | 'danger' {
  if (s === 'completed') return 'success'
  if (s === 'failed' || s === 'dropped') return 'danger'
  return 'default'
}
</script>

<template>
  <UiDrawer :open="open" :title="student?.full_name ?? ''" @close="emit('close')">
    <div v-if="student" class="space-y-4">
      <div class="text-[12px] text-muted-foreground font-mono">
        {{ student.email ?? '—' }}
        <span v-if="student.group_name"> · {{ student.group_name }}</span>
      </div>

      <h3 class="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">
        {{ t('teacher_students.col_courses') }} ({{ courses.length }})
      </h3>

      <div v-if="loading" class="text-[13px] text-muted-foreground">…</div>
      <div v-else-if="courses.length === 0" class="text-[13px] text-muted-foreground italic">
        —
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="c in courses"
          :key="c.course_id"
          class="border border-border rounded-md p-3"
        >
          <div class="flex items-start justify-between gap-2 mb-2">
            <span class="text-[13px] font-medium">{{ c.course_title }}</span>
            <UiBadge :variant="statusVariant(c.completion_status)">
              {{ t(`students.completion_${c.completion_status}`) }}
            </UiBadge>
          </div>
          <div class="flex items-center gap-3">
            <UiProgressBar :value="Math.round(c.progress_percent)" />
            <span class="font-mono text-[11px] text-muted-foreground shrink-0 tabular-nums">
              {{ Math.round(c.progress_percent) }}%
            </span>
            <span
              v-if="c.final_grade !== null"
              class="font-mono text-[11px] shrink-0 tabular-nums text-foreground"
            >
              · {{ c.final_grade.toFixed(1) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </UiDrawer>
</template>
