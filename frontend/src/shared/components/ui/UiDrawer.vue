<script setup lang="ts">
import { TransitionRoot, TransitionChild, Dialog, DialogPanel } from '@headlessui/vue'
import { useI18n } from 'vue-i18n'

interface Props {
  open: boolean
  title?: string
  width?: 'sm' | 'md' | 'lg'
}

const { t } = useI18n()

withDefaults(defineProps<Props>(), {
  title: '',
  width: 'md',
})

const emit = defineEmits<{ close: [] }>()

// Phase 8d — mobile'da full screen, sm:max-w-* dan boshlab cheklov.
// Mobile foydalanuvchi bo'sh joydan to'liq foydalanadi.
const widthClass = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-2xl',
}
</script>

<template>
  <TransitionRoot :show="open" as="template">
    <Dialog as="div" class="relative z-50" @close="emit('close')">
      <!-- Backdrop -->
      <TransitionChild
        as="template"
        enter="ease-out duration-200"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-150"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-foreground/30" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-hidden">
        <div class="absolute inset-0 overflow-hidden">
          <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full sm:pl-10">
            <TransitionChild
              as="template"
              enter="transform transition ease-in-out duration-300"
              enter-from="translate-x-full"
              enter-to="translate-x-0"
              leave="transform transition ease-in-out duration-200"
              leave-from="translate-x-0"
              leave-to="translate-x-full"
            >
              <DialogPanel
                :class="['pointer-events-auto w-screen', widthClass[width]]"
              >
                <div class="flex h-full flex-col bg-background border-l border-border shadow-xl">
                  <header
                    v-if="title || $slots.header"
                    class="px-6 py-4 border-b border-border flex items-center justify-between"
                  >
                    <div>
                      <slot name="header">
                        <div class="mono-tag mb-0.5">Drawer</div>
                        <h2 class="text-lg font-semibold text-foreground">{{ title }}</h2>
                      </slot>
                    </div>
                    <button
                      type="button"
                      class="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                      :aria-label="t('a11y.close')"
                      @click="emit('close')"
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        aria-hidden="true"
                      >
                        <path d="M18 6 6 18M6 6l12 12" />
                      </svg>
                    </button>
                  </header>

                  <div class="flex-1 overflow-y-auto p-6">
                    <slot />
                  </div>

                  <footer
                    v-if="$slots.footer"
                    class="px-6 py-4 border-t border-border bg-muted/40"
                  >
                    <slot name="footer" />
                  </footer>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
