<script setup lang="ts">
interface Props {
  modelValue: string | number | null | undefined
  type?: 'text' | 'email' | 'password' | 'tel' | 'number' | 'search' | 'url' | 'datetime-local'
  placeholder?: string
  required?: boolean
  disabled?: boolean
  autocomplete?: string
  hasError?: boolean
  min?: number | string
  max?: number | string
  step?: number | string
  minlength?: number | string
  maxlength?: number | string
  pattern?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  placeholder: '',
  required: false,
  disabled: false,
  autocomplete: 'off',
  hasError: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

function onInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value
  // type=number — bo'sh string'ni '' deb yuboramiz, aks holda Number
  if (props.type === 'number') {
    if (raw === '') {
      emit('update:modelValue', '')
    } else {
      const n = Number(raw)
      emit('update:modelValue', Number.isNaN(n) ? raw : n)
    }
  } else {
    emit('update:modelValue', raw)
  }
}
</script>

<template>
  <input
    :type="type"
    :value="modelValue ?? ''"
    :placeholder="placeholder"
    :required="required"
    :disabled="disabled"
    :autocomplete="autocomplete"
    :min="min"
    :max="max"
    :step="step"
    :minlength="minlength"
    :maxlength="maxlength"
    :pattern="pattern"
    @input="onInput"
    :class="[
      'block w-full rounded-md border px-3 py-2 text-[13px]',
      'bg-background text-foreground placeholder:text-muted-foreground',
      'focus:outline-none focus:border-foreground focus:shadow-focus',
      'disabled:bg-muted disabled:cursor-not-allowed',
      hasError ? 'border-danger-500' : 'border-border-strong',
    ]"
  />
</template>
