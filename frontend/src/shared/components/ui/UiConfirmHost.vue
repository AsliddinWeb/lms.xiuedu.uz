<script setup lang="ts">
/**
 * Phase 8a — Confirm dialog host (mounted once at App root).
 *
 * `useConfirm()` orqali imperative chaqirilgan dialog'larni render qiladi.
 */
import { confirmState, resolveConfirm } from '@shared/composables/useConfirm'
import UiDialog from '@shared/components/ui/UiDialog.vue'
</script>

<template>
  <UiDialog
    :open="confirmState.open"
    :title="confirmState.title"
    :description="confirmState.description"
    :confirm-label="confirmState.confirmLabel"
    :cancel-label="confirmState.cancelLabel"
    :variant="confirmState.variant"
    :alert-mode="confirmState.alertMode"
    @confirm="resolveConfirm(true)"
    @cancel="resolveConfirm(false)"
  />
</template>
