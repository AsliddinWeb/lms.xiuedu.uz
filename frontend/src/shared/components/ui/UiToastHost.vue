<script setup lang="ts">
/**
 * Phase 8a — Toast notification host (mounted once at App root).
 *
 * Top-right joylashadi. Keyboard yo'naltirilmaydi (aria-live polite).
 */
import { dismiss, toastState, type ToastVariant } from '@shared/composables/useToast'

const variantClass: Record<ToastVariant, string> = {
  success:
    'bg-success-50 border-success-200 text-success-700 dark:bg-success-700/15 dark:border-success-700/40 dark:text-success-200',
  error:
    'bg-danger-50 border-danger-200 text-danger-700 dark:bg-danger-700/15 dark:border-danger-700/40 dark:text-danger-200',
  info: 'bg-info-50 border-info-200 text-info-700 dark:bg-info-700/15 dark:border-info-700/40 dark:text-info-200',
  warning:
    'bg-warning-50 border-warning-200 text-warning-700 dark:bg-warning-700/15 dark:border-warning-700/40 dark:text-warning-200',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-[70] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="true"
    >
      <TransitionGroup
        enter-active-class="transition ease-out duration-200"
        enter-from-class="translate-x-4 opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-for="t in toastState.items"
          :key="t.id"
          :class="[
            'pointer-events-auto rounded-md border px-3 py-2 shadow-md text-[13px] max-w-sm flex items-start gap-2',
            variantClass[t.variant],
          ]"
          role="status"
        >
          <span class="flex-1 whitespace-pre-wrap">{{ t.message }}</span>
          <button
            type="button"
            class="opacity-60 hover:opacity-100 text-[16px] leading-none"
            :aria-label="'Close notification'"
            @click="dismiss(t.id)"
          >
            ×
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
