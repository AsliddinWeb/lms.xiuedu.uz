<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { enrollmentsApi } from '@shared/api/courses'
import { usersApi } from '@shared/api/users'
import { extractErrorMessage } from '@shared/api/client'
import type { EnrollmentMethod } from '@shared/types/courses'
import type { UserListItem } from '@shared/types/users'

interface Props {
  open: boolean
  courseId: number
}
const props = defineProps<Props>()
const emit = defineEmits<{ close: []; added: [] }>()

const { t } = useI18n()

const searchQ = ref('')
const results = ref<UserListItem[]>([])
const selected = ref<UserListItem | null>(null)
const method = ref<EnrollmentMethod>('manual')
const errorMsg = ref<string | null>(null)
const loading = ref(false)
const submitting = ref(false)

const methodOptions = [
  { value: 'manual', label: 'manual' },
  { value: 'auto', label: 'auto' },
]

watch(
  () => props.open,
  (open) => {
    if (open) {
      searchQ.value = ''
      results.value = []
      selected.value = null
      method.value = 'manual'
      errorMsg.value = null
    }
  },
)

let timer: ReturnType<typeof setTimeout> | null = null
watch(searchQ, (q) => {
  if (timer) clearTimeout(timer)
  if (!q || q.trim().length < 2) {
    results.value = []
    return
  }
  timer = setTimeout(async () => {
    loading.value = true
    try {
      const data = await usersApi.list({ q: q.trim(), role: 'student', page_size: 20 })
      results.value = data.items
    } catch (e) {
      errorMsg.value = extractErrorMessage(e, t('common.load_error'))
    } finally {
      loading.value = false
    }
  }, 250)
})

async function handleSubmit() {
  if (!selected.value) return
  submitting.value = true
  errorMsg.value = null
  try {
    await enrollmentsApi.addStudent(props.courseId, selected.value.id, method.value)
    emit('added')
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, "Qo'shishda xato")
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer
    :open="open"
    :title="t('user_picker.drawer_title')"
    width="md"
    @close="emit('close')"
  >
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <UiFormField :label="t('user_picker.search_placeholder')">
      <input
        v-model="searchQ"
        :placeholder="t('user_picker.search_placeholder')"
        class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
      />
    </UiFormField>

    <div v-if="loading" class="text-center py-4 text-muted-foreground text-[13px]">
      {{ t('common.loading') }}
    </div>

    <div
      v-else-if="searchQ.trim().length >= 2 && results.length === 0"
      class="text-center py-4 text-muted-foreground text-[13px] italic"
    >
      {{ t('user_picker.no_results') }}
    </div>

    <div v-else-if="results.length > 0" class="max-h-72 overflow-y-auto border border-border rounded-md mb-3">
      <button
        v-for="u in results"
        :key="u.id"
        type="button"
        class="w-full text-left px-3 py-2 hover:bg-muted/50 transition-colors flex items-center gap-2"
        :class="selected?.id === u.id ? 'bg-foreground text-background hover:bg-foreground' : ''"
        @click="selected = u"
      >
        <div class="flex-1 min-w-0">
          <div class="text-[13px] font-medium truncate">{{ u.full_name }}</div>
          <div
            class="font-mono text-[11px] truncate"
            :class="selected?.id === u.id ? 'text-background/70' : 'text-muted-foreground'"
          >
            {{ u.email }}
          </div>
        </div>
        <UiBadge v-if="!u.is_active" variant="warning">inactive</UiBadge>
      </button>
    </div>

    <div
      v-if="selected"
      class="mb-4 p-3 border border-border rounded-md bg-muted/30 text-[13px]"
    >
      {{ t('user_picker.selected', { name: selected.full_name }) }}
    </div>

    <UiFormField :label="t('user_picker.method_label')">
      <UiSelect v-model="method" :options="methodOptions" />
    </UiFormField>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('common.cancel') }}
        </UiButton>
        <UiButton :loading="submitting" :disabled="!selected" @click="handleSubmit">
          {{ t('user_picker.submit') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
