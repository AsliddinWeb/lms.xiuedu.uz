<script setup lang="ts">
/**
 * Pedagog — Talabalar (barcha kurslari bo'yicha noyob talabalar).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { enrollmentsApi } from '@shared/api/courses'
import { chatApi } from '@shared/api/chat'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import type { TeacherStudent } from '@shared/types/courses'
import StudentDrawer from './StudentDrawer.vue'

const { t } = useI18n()
const router = useRouter()

const items = ref<TeacherStudent[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref<string | null>(null)
const searchQ = ref('')
const messagingId = ref<number | null>(null)
const drawerOpen = ref(false)
const selected = ref<TeacherStudent | null>(null)

function openDetail(s: TeacherStudent) {
  selected.value = s
  drawerOpen.value = true
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await enrollmentsApi.myStudents({
      q: searchQ.value.trim() || undefined,
      page_size: 200,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQ, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})

onMounted(load)

function initials(name: string): string {
  return (
    name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? '')
      .join('') || '?'
  )
}

const gradeColor = (g: number | null) =>
  g === null
    ? 'text-muted-foreground'
    : g >= 86
      ? 'text-success-600'
      : g >= 55
        ? 'text-foreground'
        : 'text-danger-600'

async function messageStudent(s: TeacherStudent) {
  messagingId.value = s.user_id
  try {
    await chatApi.openDirect(s.user_id)
    router.push({ name: 'chat' })
  } catch (e) {
    toast.error(extractErrorMessage(e, t('common.save_error')))
  } finally {
    messagingId.value = null
  }
}

const countLabel = computed(() => total.value)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('nav.students')]"
    class="mb-4"
  />

  <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="page-title mb-1.5">{{ t('nav.students') }}</h1>
      <p class="page-subtitle">{{ t('teacher_students.subtitle') }}</p>
    </div>
    <span class="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
      {{ countLabel }} {{ t('teacher_students.total_short') }}
    </span>
  </div>

  <div class="mb-5 max-w-[340px]">
    <UiInput
      v-model="searchQ"
      type="search"
      :placeholder="t('teacher_students.search_placeholder')"
    />
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <UiCard no-padding>
    <div v-if="loading && items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="items.length === 0" class="p-8 text-center text-muted-foreground">
      {{ t('teacher_students.empty') }}
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="bg-muted">
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('students.col_name') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('teacher_students.col_group') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('teacher_students.col_courses') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('teacher_students.col_completed') }}
            </th>
            <th scope="col" class="text-left px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {{ t('teacher_students.col_avg') }}
            </th>
            <th scope="col" class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in items"
            :key="s.user_id"
            class="border-t border-border hover:bg-muted/30"
          >
            <td class="px-4 py-3 align-top">
              <div class="flex items-center gap-3">
                <span
                  class="w-8 h-8 rounded-full shrink-0 grid place-items-center text-[11px] font-semibold bg-muted text-foreground/80 overflow-hidden"
                >
                  <img
                    v-if="s.avatar_url"
                    :src="s.avatar_url"
                    :alt="s.full_name"
                    class="w-full h-full object-cover"
                  />
                  <template v-else>{{ initials(s.full_name) }}</template>
                </span>
                <div class="min-w-0">
                  <div class="font-medium truncate">{{ s.full_name }}</div>
                  <div class="font-mono text-[11px] text-muted-foreground truncate">
                    {{ s.email ?? '—' }}
                  </div>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 align-top font-mono text-[12px]">
              {{ s.group_name ?? '—' }}
            </td>
            <td class="px-4 py-3 align-top font-mono tabular-nums">
              {{ s.course_count }}
            </td>
            <td class="px-4 py-3 align-top font-mono tabular-nums text-muted-foreground">
              {{ s.completed_count }} / {{ s.course_count }}
            </td>
            <td class="px-4 py-3 align-top font-mono tabular-nums" :class="gradeColor(s.avg_grade)">
              {{ s.avg_grade !== null ? s.avg_grade.toFixed(1) : '—' }}
            </td>
            <td class="px-4 py-3 align-top text-right">
              <div class="flex justify-end gap-1.5">
                <UiButton variant="ghost" size="sm" @click="openDetail(s)">
                  {{ t('teacher_students.detail') }}
                </UiButton>
                <UiButton
                  variant="outline"
                  size="sm"
                  :loading="messagingId === s.user_id"
                  @click="messageStudent(s)"
                >
                  {{ t('teacher_students.message') }}
                </UiButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </UiCard>

  <StudentDrawer
    :open="drawerOpen"
    :student="selected"
    @close="drawerOpen = false"
  />
</template>
