<script setup lang="ts">
/**
 * Wireframe `.tabs` — flex 4px gap, 1px border-bottom, 24px mb.
 * `.tab` — 10x16 padding, 13px weight 500, mute, transparent
 * `.tab.active` — foreground, 2px border-bottom foreground
 *
 * Phase 8b — ARIA tablist pattern:
 *   - container role="tablist"
 *   - har bir tugma role="tab", aria-selected, tabindex (active=0, others=-1)
 *   - klaviatura: ArrowLeft/Right o'tish, Home/End birinchi/oxirgiga
 */
import { computed, nextTick, ref } from 'vue'

interface Tab {
  id: string
  label: string
  count?: number | string
  disabled?: boolean
}
interface Props {
  modelValue: string
  tabs: Tab[]
  /** Tablist uchun ARIA label (screen reader uchun). */
  ariaLabel?: string
}
const props = withDefaults(defineProps<Props>(), { ariaLabel: '' })
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()

const buttonRefs = ref<HTMLButtonElement[]>([])

const enabledIndices = computed(() =>
  props.tabs.reduce<number[]>((acc, t, i) => {
    if (!t.disabled) acc.push(i)
    return acc
  }, []),
)

function select(id: string, disabled?: boolean) {
  if (disabled) return
  emit('update:modelValue', id)
}

async function focusTab(idx: number) {
  await nextTick()
  buttonRefs.value[idx]?.focus()
}

function onKey(e: KeyboardEvent, currentIdx: number) {
  const enabled = enabledIndices.value
  if (enabled.length === 0) return
  const posInEnabled = enabled.indexOf(currentIdx)
  let nextIdx = currentIdx

  if (e.key === 'ArrowRight') {
    e.preventDefault()
    nextIdx = enabled[(posInEnabled + 1) % enabled.length]
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    nextIdx = enabled[(posInEnabled - 1 + enabled.length) % enabled.length]
  } else if (e.key === 'Home') {
    e.preventDefault()
    nextIdx = enabled[0]
  } else if (e.key === 'End') {
    e.preventDefault()
    nextIdx = enabled[enabled.length - 1]
  } else {
    return
  }

  const tab = props.tabs[nextIdx]
  if (tab) {
    emit('update:modelValue', tab.id)
    void focusTab(nextIdx)
  }
}

function setButtonRef(el: Element | null, idx: number) {
  if (el instanceof HTMLButtonElement) buttonRefs.value[idx] = el
}
</script>

<template>
  <div
    class="flex gap-1 border-b border-border mb-6"
    role="tablist"
    :aria-label="ariaLabel || undefined"
  >
    <button
      v-for="(tab, idx) in tabs"
      :key="tab.id"
      :ref="(el) => setButtonRef(el as Element | null, idx)"
      type="button"
      role="tab"
      :id="`tab-${tab.id}`"
      :aria-selected="modelValue === tab.id"
      :aria-controls="`tabpanel-${tab.id}`"
      :tabindex="modelValue === tab.id ? 0 : -1"
      class="px-4 py-2.5 text-[13px] font-medium border-b-2 -mb-px transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
      :class="
        modelValue === tab.id
          ? 'border-foreground text-foreground'
          : 'border-transparent text-muted-foreground hover:text-foreground'
      "
      :disabled="tab.disabled"
      @click="select(tab.id, tab.disabled)"
      @keydown="onKey($event, idx)"
    >
      <span>{{ tab.label }}</span>
      <span
        v-if="tab.count !== undefined"
        class="font-mono text-[11px] text-muted-foreground"
      >({{ tab.count }})</span>
    </button>
  </div>
</template>
