<script setup lang="ts">
/**
 * Phase 8f — Reusable date range filter.
 *
 * Ikkita native `<input type="date">` — from va to. ISO format (`YYYY-MM-DD`)
 * v-model orqali qaytaradi. Bo'sh string = filtr o'chirilgan.
 *
 * Usage:
 *   const range = ref<{from: string, to: string}>({from: '', to: ''})
 *   <UiDateRange v-model="range" />
 *
 * Native date input shadcn'da qiyin, lekin Geist style'ga mos. Browser
 * date picker'i dark mode'da default rang ko'rsatadi — accept qilamiz.
 */

import { useI18n } from 'vue-i18n'

interface DateRange {
  from: string
  to: string
}

interface Props {
  modelValue: DateRange
  fromLabel?: string
  toLabel?: string
  /** Maks date — default bugun. */
  max?: string
}

const props = withDefaults(defineProps<Props>(), {
  fromLabel: '',
  toLabel: '',
  max: '',
})

const emit = defineEmits<{ 'update:modelValue': [v: DateRange] }>()
const { t } = useI18n()

function update(field: 'from' | 'to', value: string) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

function clear() {
  emit('update:modelValue', { from: '', to: '' })
}
</script>

<template>
  <div class="flex items-center gap-2 flex-wrap">
    <label class="flex items-center gap-1.5 text-[12px] text-muted-foreground">
      <span class="font-mono uppercase tracking-wider">
        {{ fromLabel || t('date_range.from') }}
      </span>
      <input
        type="date"
        :value="modelValue.from"
        :max="modelValue.to || max"
        class="bg-background border border-border-strong rounded-md px-2 py-1.5 text-[13px] outline-none focus:border-foreground focus:shadow-focus"
        @change="update('from', ($event.target as HTMLInputElement).value)"
      />
    </label>
    <span class="text-muted-foreground" aria-hidden="true">→</span>
    <label class="flex items-center gap-1.5 text-[12px] text-muted-foreground">
      <span class="font-mono uppercase tracking-wider">
        {{ toLabel || t('date_range.to') }}
      </span>
      <input
        type="date"
        :value="modelValue.to"
        :min="modelValue.from"
        :max="max"
        class="bg-background border border-border-strong rounded-md px-2 py-1.5 text-[13px] outline-none focus:border-foreground focus:shadow-focus"
        @change="update('to', ($event.target as HTMLInputElement).value)"
      />
    </label>
    <button
      v-if="modelValue.from || modelValue.to"
      type="button"
      class="text-[12px] text-muted-foreground hover:text-foreground px-2 py-1.5"
      :aria-label="t('date_range.clear')"
      @click="clear"
    >
      ✕
    </button>
  </div>
</template>
