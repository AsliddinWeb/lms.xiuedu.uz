<script setup lang="ts">
/**
 * Eksport dropdown — CSV / Excel / PDF (brendlangan, logo bilan).
 * `build` thunk bosilganda joriy ma'lumotdan ExportSpec yasaydi (lazy).
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'

import { exportTable, type ExportFormat, type ExportSpec } from '@shared/utils/export'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'

interface Props {
  /** Bosilganda joriy ma'lumotdan ExportSpec yasaydi */
  build: () => ExportSpec | Promise<ExportSpec>
  disabled?: boolean
  label?: string
  size?: 'sm' | 'md'
}
const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  label: '',
  size: 'md',
})

const { t } = useI18n()
const busy = ref<ExportFormat | null>(null)

const formats: Array<{ key: ExportFormat; label: string; ext: string }> = [
  { key: 'xlsx', label: 'Excel', ext: 'XLSX' },
  { key: 'pdf', label: 'PDF', ext: 'PDF' },
  { key: 'csv', label: 'CSV', ext: 'CSV' },
]

async function run(format: ExportFormat) {
  if (busy.value) return
  busy.value = format
  try {
    const spec = await props.build()
    await exportTable(format, spec)
  } catch (e) {
    toast.error(extractErrorMessage(e, t('export.error')))
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <Menu as="div" class="relative inline-block text-left">
    <MenuButton
      :disabled="disabled || !!busy"
      :class="[
        'inline-flex items-center gap-2 rounded-md border border-border bg-background font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed',
        size === 'sm' ? 'px-2.5 py-1.5 text-[12px]' : 'px-3 py-2 text-[13px]',
      ]"
    >
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M7.5 1.5v8M4.5 6.5l3 3 3-3M2.5 12.5h10" />
      </svg>
      <span>{{ label || t('export.button') }}</span>
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 4.5 6 7.5l3-3" />
      </svg>
    </MenuButton>

    <transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <MenuItems
        class="absolute right-0 mt-1.5 w-48 origin-top-right rounded-md border border-border bg-background shadow-lg z-50 focus:outline-none overflow-hidden p-1"
      >
        <div class="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          {{ t('export.heading') }}
        </div>
        <MenuItem v-for="f in formats" :key="f.key" v-slot="{ active }" as="template">
          <button
            type="button"
            :disabled="!!busy"
            :class="[
              'w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-left transition-colors disabled:opacity-50',
              active ? 'bg-muted' : '',
            ]"
            @click="run(f.key)"
          >
            <span class="font-mono text-[10px] font-semibold text-muted-foreground w-9">{{ f.ext }}</span>
            <span class="flex-1">{{ f.label }}</span>
            <svg v-if="busy === f.key" class="animate-spin text-muted-foreground" width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="3" class="opacity-25" />
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
            </svg>
          </button>
        </MenuItem>
      </MenuItems>
    </transition>
  </Menu>
</template>
