<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { extractErrorMessage } from '@shared/api/client'
import { apiClient } from '@shared/api/client'
import type { AcademicCalendar } from '@shared/types/academic'

const { t } = useI18n()

interface Props {
  open: boolean
  calendar?: AcademicCalendar | null
}
const props = withDefaults(defineProps<Props>(), { calendar: null })
const emit = defineEmits<{ close: []; saved: [] }>()

const academicYear = ref('')
const name = ref('')
const startDate = ref('')
const endDate = ref('')
const isActive = ref(true)

interface SemesterRow {
  name: string
  start_date: string
  end_date: string
}
interface HolidayRow {
  name: string
  date: string
  days: number
}

const semesters = ref<SemesterRow[]>([])
const holidays = ref<HolidayRow[]>([])

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

watch(
  () => [props.open, props.calendar],
  () => {
    errorMsg.value = null
    if (!props.open) return

    if (props.calendar) {
      const c = props.calendar
      academicYear.value = c.academic_year
      name.value = c.name
      startDate.value = c.start_date
      endDate.value = c.end_date
      isActive.value = c.is_active
      semesters.value = (c.semesters as unknown as SemesterRow[]).map((s) => ({
        name: s.name ?? '',
        start_date: s.start_date ?? '',
        end_date: s.end_date ?? '',
      }))
      holidays.value = (c.holidays as unknown as HolidayRow[]).map((h) => ({
        name: h.name ?? '',
        date: h.date ?? '',
        days: typeof h.days === 'number' ? h.days : 1,
      }))
    } else {
      academicYear.value = ''
      name.value = ''
      startDate.value = ''
      endDate.value = ''
      isActive.value = true
      semesters.value = []
      holidays.value = []
    }
  },
  { immediate: true },
)

function addSemester() {
  semesters.value.push({ name: '', start_date: '', end_date: '' })
}
function removeSemester(idx: number) {
  semesters.value.splice(idx, 1)
}
function addHoliday() {
  holidays.value.push({ name: '', date: '', days: 1 })
}
function removeHoliday(idx: number) {
  holidays.value.splice(idx, 1)
}

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    const cleanedSemesters = semesters.value.filter(
      (s) => s.name && s.start_date && s.end_date,
    )
    const cleanedHolidays = holidays.value.filter((h) => h.name && h.date)

    if (props.calendar) {
      await apiClient.patch(`/academic-calendars/${props.calendar.id}`, {
        name: name.value.trim(),
        start_date: startDate.value,
        end_date: endDate.value,
        semesters: cleanedSemesters,
        holidays: cleanedHolidays,
        is_active: isActive.value,
      })
    } else {
      await apiClient.post('/academic-calendars', {
        // Single-tenant XIU: organization_id'ni backend service avto-to'ldiradi
        academic_year: academicYear.value.trim(),
        name: name.value.trim(),
        start_date: startDate.value,
        end_date: endDate.value,
        semesters: cleanedSemesters,
        holidays: cleanedHolidays,
        is_active: isActive.value,
      })
    }
    emit('saved')
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
    :title="calendar ? t('calendar.edit_title') : t('calendar.create_title')"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="cal-form" @submit.prevent="handleSubmit">
      <!-- Single-tenant XIU: organization_id avto-fill, picker olib tashlandi -->

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('calendar.field_year')" :hint="t('calendar.field_year_hint')" required>
          <UiInput v-model="academicYear" required :disabled="!!calendar" placeholder="2026-2027" />
        </UiFormField>
        <UiFormField :label="t('calendar.field_name')" required>
          <UiInput v-model="name" required />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('calendar.field_start')" required>
          <UiInput v-model="startDate" type="text" placeholder="2026-09-01" required />
        </UiFormField>
        <UiFormField :label="t('calendar.field_end')" required>
          <UiInput v-model="endDate" type="text" placeholder="2027-06-30" required />
        </UiFormField>
      </div>

      <!-- Semesters editor -->
      <div class="mt-2">
        <div class="flex items-center justify-between mb-2">
          <div class="text-xs font-medium text-foreground">
            {{ t('calendar.section_semesters') }} ({{ semesters.length }})
          </div>
          <UiButton type="button" variant="outline" size="sm" @click="addSemester">
            {{ t('calendar.add_semester') }}
          </UiButton>
        </div>

        <div
          v-if="semesters.length === 0"
          class="text-[12px] text-muted-foreground italic p-3 border border-border rounded-md"
        >
          {{ t('calendar.no_semesters') }}
        </div>

        <div v-else class="border border-border rounded-md divide-y divide-border">
          <div v-for="(s, idx) in semesters" :key="idx" class="grid grid-cols-[1fr_120px_120px_auto] gap-2 p-2 items-center">
            <UiInput v-model="s.name" :placeholder="t('calendar.semester_name_placeholder')" />
            <UiInput v-model="s.start_date" placeholder="YYYY-MM-DD" />
            <UiInput v-model="s.end_date" placeholder="YYYY-MM-DD" />
            <button
              type="button"
              @click="removeSemester(idx)"
              class="text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-700/15 rounded p-1.5"
              :title="t('calendar.delete_row')"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round">
                <path d="M3 3l8 8M11 3l-8 8" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Holidays editor -->
      <div class="mt-4">
        <div class="flex items-center justify-between mb-2">
          <div class="text-xs font-medium text-foreground">
            {{ t('calendar.section_holidays') }} ({{ holidays.length }})
          </div>
          <UiButton type="button" variant="outline" size="sm" @click="addHoliday">
            {{ t('calendar.add_holiday') }}
          </UiButton>
        </div>

        <div
          v-if="holidays.length === 0"
          class="text-[12px] text-muted-foreground italic p-3 border border-border rounded-md"
        >
          {{ t('calendar.no_holidays') }}
        </div>

        <div v-else class="border border-border rounded-md divide-y divide-border">
          <div v-for="(h, idx) in holidays" :key="idx" class="grid grid-cols-[1fr_120px_80px_auto] gap-2 p-2 items-center">
            <UiInput v-model="h.name" :placeholder="t('calendar.holiday_name_placeholder')" />
            <UiInput v-model="h.date" placeholder="YYYY-MM-DD" />
            <UiInput v-model="h.days" type="number" />
            <button
              type="button"
              @click="removeHoliday(idx)"
              class="text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-700/15 rounded p-1.5"
              :title="t('calendar.delete_row')"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round">
                <path d="M3 3l8 8M11 3l-8 8" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <label class="flex items-center gap-2 mt-4 mb-4 cursor-pointer">
        <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
        <span class="text-[13px]">{{ t('common.active') }}</span>
      </label>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton type="submit" form="cal-form" :loading="submitting">
          {{ calendar ? t('common.save') : t('common.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
