<script setup lang="ts">
/**
 * Phase 8a — Confirm / Alert modal dialog.
 *
 * `window.confirm` o'rniga ishlatiladigan modal. `useConfirm()` composable
 * orqali imperative API mavjud, lekin to'g'ridan-to'g'ri ham ishlatish mumkin.
 */
import { TransitionRoot, TransitionChild, Dialog, DialogPanel, DialogTitle } from '@headlessui/vue'
import UiButton from '@shared/components/ui/UiButton.vue'

interface Props {
  open: boolean
  title?: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'danger'
  /** Faqat OK tugmasi (alert holati) */
  alertMode?: boolean
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  title: '',
  description: '',
  confirmLabel: '',
  cancelLabel: '',
  variant: 'default',
  alertMode: false,
  loading: false,
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <TransitionRoot :show="open" as="template">
    <Dialog as="div" class="relative z-[60]" @close="emit('cancel')">
      <TransitionChild
        as="template"
        enter="ease-out duration-200"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-150"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-foreground/40" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <TransitionChild
            as="template"
            enter="ease-out duration-200"
            enter-from="opacity-0 scale-95"
            enter-to="opacity-100 scale-100"
            leave="ease-in duration-150"
            leave-from="opacity-100 scale-100"
            leave-to="opacity-0 scale-95"
          >
            <DialogPanel
              class="w-full max-w-md transform overflow-hidden rounded-lg bg-background border border-border shadow-xl"
              role="alertdialog"
              :aria-modal="true"
            >
              <div class="p-5">
                <div
                  v-if="variant === 'danger'"
                  class="mb-3 w-10 h-10 grid place-items-center rounded-full bg-danger-500/15 text-danger-600"
                  aria-hidden="true"
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <DialogTitle
                  v-if="title"
                  class="text-[15px] font-semibold text-foreground mb-1"
                >
                  {{ title }}
                </DialogTitle>
                <div
                  v-if="description"
                  class="text-[13px] text-muted-foreground whitespace-pre-wrap"
                >
                  {{ description }}
                </div>
                <div v-if="$slots.default" class="text-[13px] text-foreground">
                  <slot />
                </div>
              </div>
              <div
                class="px-5 py-3 bg-muted/40 border-t border-border flex justify-end gap-2"
              >
                <UiButton
                  v-if="!alertMode"
                  variant="ghost"
                  :disabled="loading"
                  @click="emit('cancel')"
                >
                  {{ cancelLabel || 'Bekor' }}
                </UiButton>
                <UiButton
                  :variant="variant === 'danger' ? 'outline' : 'primary'"
                  :class="variant === 'danger' ? 'text-danger-600 border-danger-500' : ''"
                  :loading="loading"
                  @click="emit('confirm')"
                >
                  {{ confirmLabel || 'OK' }}
                </UiButton>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
