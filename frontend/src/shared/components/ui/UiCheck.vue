<script setup lang="ts">
/**
 * Wireframe `.check` — lesson player radio dot:
 *   - empty: gray circle border
 *   - done: green filled with white ✓
 *   - locked: gray with 🔒
 *
 * 18x18 size, used in lesson list.
 */
interface Props {
  state: 'empty' | 'done' | 'locked'
  size?: number
}
withDefaults(defineProps<Props>(), { size: 18 })
</script>

<template>
  <span
    class="rounded-full border-[1.5px] grid place-items-center flex-shrink-0 text-[10px]"
    :style="{ width: `${size}px`, height: `${size}px` }"
    :class="{
      'border-border-strong': state === 'empty',
      'bg-success-600 border-success-600 text-white': state === 'done',
      'bg-muted border-border-strong text-muted-foreground': state === 'locked',
    }"
    aria-hidden="true"
  >
    <template v-if="state === 'done'">✓</template>
    <template v-else-if="state === 'locked'">🔒</template>
  </span>
</template>
