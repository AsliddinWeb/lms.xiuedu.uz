<script setup lang="ts">
/** Kichik switch (on/off) — sozlamalar uchun. */
defineProps<{ modelValue: boolean; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="relative inline-flex h-[22px] w-[40px] shrink-0 items-center rounded-full transition-colors outline-none focus-visible:shadow-focus disabled:opacity-50 disabled:cursor-not-allowed"
    :class="modelValue ? 'bg-foreground' : 'bg-border-strong'"
    @click="emit('update:modelValue', !modelValue)"
  >
    <span
      class="inline-block h-[16px] w-[16px] rounded-full bg-background shadow-sm transition-transform"
      :class="modelValue ? 'translate-x-[21px]' : 'translate-x-[3px]'"
    ></span>
  </button>
</template>
