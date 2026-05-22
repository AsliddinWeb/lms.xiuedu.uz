<script setup lang="ts">
interface Option {
  value: string | number | null
  label: string
}

interface Props {
  modelValue: string | number | null
  options: Option[]
  placeholder?: string
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  placeholder: '',
  disabled: false,
})

defineEmits<{
  'update:modelValue': [value: string | number | null]
}>()
</script>

<template>
  <select
    :value="modelValue ?? ''"
    :disabled="disabled"
    @change="
      $emit(
        'update:modelValue',
        ($event.target as HTMLSelectElement).value === ''
          ? null
          : ($event.target as HTMLSelectElement).value,
      )
    "
    class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus disabled:bg-muted disabled:cursor-not-allowed"
  >
    <option v-if="placeholder" value="">{{ placeholder }}</option>
    <option v-for="opt in options" :key="String(opt.value)" :value="opt.value as never">
      {{ opt.label }}
    </option>
  </select>
</template>
