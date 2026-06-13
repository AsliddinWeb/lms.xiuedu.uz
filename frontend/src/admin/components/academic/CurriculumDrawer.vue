<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { extractErrorMessage } from '@shared/api/client'
import { curriculaApi, specialtiesApi, subjectsApi } from '@shared/api/academic'
import type { Curriculum, Specialty, Subject } from '@shared/types/academic'

interface Props {
  open: boolean
  curriculum?: Curriculum | null
}
const props = withDefaults(defineProps<Props>(), { curriculum: null })
const emit = defineEmits<{ close: []; saved: [] }>()

const allSpecialties = ref<Specialty[]>([])
const allSubjects = ref<Subject[]>([])

const specialtyId = ref<number | null>(null)
const name = ref('')
const version = ref('')
const validFrom = ref('')
const validUntil = ref('')
const basedOn = ref<string | null>('DTS')
const standardCode = ref('')
const totalCredits = ref(240)

interface RowItem {
  subject_id: number | null
  semester: number
  is_required: boolean
}
const rows = ref<RowItem[]>([])

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

const spOptions = computed(() =>
  allSpecialties.value.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` })),
)
const subjectOptions = computed(() =>
  allSubjects.value.map((s) => ({ value: s.id, label: `${s.code} — ${s.name} (${s.credits}c)` })),
)
const basedOnOptions = [
  { value: 'DTS', label: 'DTS (Davlat ta\'lim standarti)' },
  { value: 'professional_standard', label: 'Kasbiy standart' },
]

watch(
  () => [props.open, props.curriculum],
  async () => {
    errorMsg.value = null
    if (!props.open) return

    const [sp, subs] = await Promise.all([
      specialtiesApi.list({ page_size: 200 }),
      subjectsApi.list({ page_size: 500 }),
    ])
    allSpecialties.value = sp.items
    allSubjects.value = subs.items

    if (props.curriculum) {
      const c = props.curriculum
      specialtyId.value = c.specialty_id
      name.value = c.name
      version.value = c.version ?? ''
      validFrom.value = c.valid_from
      validUntil.value = c.valid_until ?? ''
      basedOn.value = c.based_on
      standardCode.value = c.standard_code ?? ''
      totalCredits.value = c.total_credits
      rows.value = c.subjects.map((cs) => ({
        subject_id: cs.subject_id,
        semester: cs.semester,
        is_required: cs.is_required,
      }))
    } else {
      specialtyId.value = allSpecialties.value[0]?.id ?? null
      name.value = ''
      version.value = ''
      validFrom.value = ''
      validUntil.value = ''
      basedOn.value = 'DTS'
      standardCode.value = ''
      totalCredits.value = 240
      rows.value = []
    }
  },
  { immediate: true },
)

function addRow() {
  rows.value.push({ subject_id: null, semester: 1, is_required: true })
}
function removeRow(idx: number) {
  rows.value.splice(idx, 1)
}

const groupedBySemester = computed(() => {
  const map: Record<number, RowItem[]> = {}
  for (const r of rows.value) {
    if (!map[r.semester]) map[r.semester] = []
    map[r.semester].push(r)
  }
  return Object.entries(map)
    .map(([k, v]) => ({ semester: Number(k), items: v }))
    .sort((a, b) => a.semester - b.semester)
})

async function handleSubmit() {
  errorMsg.value = null
  if (!specialtyId.value) {
    errorMsg.value = 'Yo\'nalish tanlanmagan'
    return
  }
  if (!validFrom.value) {
    errorMsg.value = 'valid_from sanasi kerak'
    return
  }
  submitting.value = true
  try {
    const validRows = rows.value.filter((r) => r.subject_id != null) as Array<{
      subject_id: number
      semester: number
      is_required: boolean
    }>
    if (props.curriculum) {
      // Update — fanlar Phase 2a'da uchun update qilinmaydi (faqat metadata)
      await curriculaApi.update(props.curriculum.id, {
        name: name.value.trim(),
        version: version.value.trim() || null,
        valid_from: validFrom.value,
        valid_until: validUntil.value || null,
        based_on: basedOn.value,
        standard_code: standardCode.value.trim() || null,
        total_credits: totalCredits.value,
      })
    } else {
      await curriculaApi.create({
        specialty_id: specialtyId.value,
        name: name.value.trim(),
        version: version.value.trim() || null,
        valid_from: validFrom.value,
        valid_until: validUntil.value || null,
        based_on: basedOn.value,
        standard_code: standardCode.value.trim() || null,
        total_credits: totalCredits.value,
        subjects: validRows,
      })
    }
    emit('saved')
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, 'Saqlashda xato')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="curriculum ? 'O\'quv reja tahrir' : 'Yangi o\'quv reja'"
    width="lg"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <UiAlert v-if="curriculum" variant="info" class="mb-4">
      Tahrir rejimida fanlar ro'yxati read-only. Yangi versiya yaratish uchun
      <strong>Clone</strong> tugmasini ishlating.
    </UiAlert>

    <form id="curr-form" @submit.prevent="handleSubmit">
      <UiFormField label="Yo'nalish" required>
        <UiSelect v-model="specialtyId" :options="spOptions" :disabled="!!curriculum" />
      </UiFormField>

      <UiFormField label="Reja nomi" required>
        <UiInput v-model="name" required placeholder="Dasturiy injiniring 2026-2030" />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField label="Versiya">
          <UiInput v-model="version" placeholder="2026-v1" />
        </UiFormField>
        <UiFormField label="Jami kreditlar" required>
          <UiInput v-model="totalCredits" type="number" required />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField label="Boshlanish (valid_from)" required>
          <UiInput v-model="validFrom" type="text" placeholder="2026-09-01" required />
        </UiFormField>
        <UiFormField label="Tugash (valid_until)">
          <UiInput v-model="validUntil" type="text" placeholder="2030-06-30" />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField label="Asosi">
          <UiSelect v-model="basedOn" :options="basedOnOptions" placeholder="Belgilanmagan" />
        </UiFormField>
        <UiFormField label="Standart kodi">
          <UiInput v-model="standardCode" placeholder="OʻzDSt 36.2030" />
        </UiFormField>
      </div>

      <div v-if="!curriculum" class="mt-4">
        <div class="flex items-center justify-between mb-2">
          <div class="text-xs font-medium text-foreground">
            Fanlar va semestr taqsimoti ({{ rows.length }})
          </div>
          <UiButton type="button" variant="outline" size="sm" @click="addRow">+ Fan qo'shish</UiButton>
        </div>

        <div v-if="rows.length === 0" class="text-[12px] text-muted-foreground italic p-3 border border-border rounded-md">
          Hech qanday fan qo'shilmagan
        </div>

        <div v-else class="border border-border rounded-md divide-y divide-border">
          <div
            v-for="(r, idx) in rows"
            :key="idx"
            class="flex items-center gap-2 p-2"
          >
            <div class="flex-1">
              <UiSelect v-model="r.subject_id" :options="subjectOptions" placeholder="Fan tanlang" />
            </div>
            <div class="w-24">
              <UiInput v-model="r.semester" type="number" placeholder="sem." />
            </div>
            <label class="flex items-center gap-1.5 px-2 cursor-pointer text-[12px]">
              <input v-model="r.is_required" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
              majburiy
            </label>
            <button
              type="button"
              @click="removeRow(idx)"
              class="text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-700/15 rounded p-1.5"
              aria-label="O'chirish"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round">
                <path d="M3 3l8 8M11 3l-8 8" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-else class="mt-4">
        <div class="text-xs font-medium text-foreground mb-2">
          Joriy fanlar ({{ groupedBySemester.length }} semestr):
        </div>
        <div class="space-y-2">
          <div
            v-for="g in groupedBySemester"
            :key="g.semester"
            class="border border-border rounded-md p-3"
          >
            <div class="mono-tag mb-1.5">Semestr {{ g.semester }}</div>
            <div class="flex flex-wrap gap-1.5">
              <UiBadge v-for="r in g.items" :key="`${g.semester}-${r.subject_id}`" variant="default">
                #{{ r.subject_id }}{{ r.is_required ? '' : ' (tanlov)' }}
              </UiBadge>
            </div>
          </div>
        </div>
      </div>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">Bekor</UiButton>
        <UiButton type="submit" form="curr-form" :loading="submitting">
          {{ curriculum ? 'Saqlash' : 'Yaratish' }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
