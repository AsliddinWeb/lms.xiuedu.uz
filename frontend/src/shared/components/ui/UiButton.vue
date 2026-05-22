<script setup lang="ts">
interface Props {
  type?: 'button' | 'submit' | 'reset'
  variant?: 'primary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  fullWidth?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'button',
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
  fullWidth: false,
})

const variantClass = {
  // wireframe: btn-primary → background: foreground (qora)
  primary: 'bg-foreground text-background hover:bg-[#27272a] border-transparent',
  outline: 'bg-background text-foreground border-border-strong hover:bg-muted',
  ghost: 'bg-transparent text-foreground border-transparent hover:bg-muted',
  danger: 'bg-danger-600 text-white border-transparent hover:bg-danger-700',
}[props.variant]

const sizeClass = {
  sm: 'px-2.5 py-1.5 text-xs gap-1.5',
  md: 'px-3.5 py-2 text-[13px] gap-2',
  lg: 'px-5 py-3 text-sm gap-2',
}[props.size]
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'inline-flex items-center justify-center rounded-md border font-medium',
      'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      variantClass,
      sizeClass,
      fullWidth && 'w-full',
    ]"
  >
    <svg
      v-if="loading"
      class="animate-spin h-3.5 w-3.5"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
    <slot />
  </button>
</template>
