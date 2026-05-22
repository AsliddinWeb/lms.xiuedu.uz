<script setup lang="ts">
import { RouterLink } from 'vue-router'

interface Props {
  label?: string
  hint?: string
  error?: string | null
  required?: boolean
  rightLink?: { label: string; to?: string; href?: string }
}

withDefaults(defineProps<Props>(), {
  label: '',
  hint: '',
  error: null,
  required: false,
  rightLink: undefined,
})
</script>

<template>
  <div class="mb-4">
    <div v-if="label" class="flex items-center justify-between mb-1.5">
      <label class="block text-xs font-medium text-foreground">
        {{ label }}
        <span v-if="required" class="text-danger-600">*</span>
      </label>
      <RouterLink
        v-if="rightLink?.to"
        :to="rightLink.to"
        class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground hover:text-foreground"
      >
        {{ rightLink.label }}
      </RouterLink>
      <a
        v-else-if="rightLink?.href"
        :href="rightLink.href"
        class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground hover:text-foreground"
      >
        {{ rightLink.label }}
      </a>
    </div>
    <slot />
    <p v-if="error" class="mt-1 text-[11px] text-danger-600">{{ error }}</p>
    <p
      v-else-if="hint"
      class="mt-1 font-mono text-[11px] text-muted-foreground"
    >
      {{ hint }}
    </p>
  </div>
</template>
