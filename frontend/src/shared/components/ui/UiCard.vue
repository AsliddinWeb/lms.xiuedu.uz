<script setup lang="ts">
interface Props {
  title?: string
  noPadding?: boolean
}

withDefaults(defineProps<Props>(), {
  title: '',
  noPadding: false,
})
</script>

<template>
  <div class="bg-background border border-border rounded-lg overflow-hidden">
    <div
      v-if="title || $slots.header"
      class="px-5 py-4 border-b border-border flex items-center justify-between"
    >
      <h3 v-if="title" class="text-sm font-semibold text-foreground">{{ title }}</h3>
      <slot name="header" />
      <slot name="actions" />
    </div>
    <div :class="noPadding ? '' : 'p-5'">
      <slot />
    </div>
  </div>
</template>
