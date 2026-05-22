<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiButton from '@shared/components/ui/UiButton.vue'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage } from '@shared/api/client'

const { t } = useI18n()

const loading = ref(false)
const url = ref<string>('')
const copied = ref(false)
const error = ref<string | null>(null)
const open = ref(false)

async function openDialog() {
  open.value = true
  error.value = null
  if (url.value) return
  loading.value = true
  try {
    const data = await liveSessionsApi.getCalendarToken()
    url.value = data.url
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function copyUrl() {
  if (!url.value) return
  try {
    await navigator.clipboard.writeText(url.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // fallback: textarea select trick not needed for modern browsers
  }
}

function close() {
  open.value = false
}
</script>

<template>
  <UiButton variant="outline" size="sm" @click="openDialog">
    <svg
      width="14" height="14" viewBox="0 0 14 14" fill="none"
      stroke="currentColor" stroke-width="2" stroke-linecap="round"
    >
      <rect x="2" y="3" width="10" height="9" rx="1" />
      <path d="M2 6h10M5 1v3M9 1v3" />
    </svg>
    {{ t('live.calendar_subscribe') }}
  </UiButton>

  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 grid place-items-center bg-foreground/40 backdrop-blur-sm"
      @click.self="close"
    >
      <div class="bg-background border border-border rounded-lg shadow-xl max-w-md w-[92vw] p-6">
        <div class="mono-tag mb-3">{{ t('live.calendar_dialog_tag') }}</div>
        <h2 class="text-base font-semibold mb-2">
          {{ t('live.calendar_dialog_title') }}
        </h2>
        <p class="text-[13px] text-muted-foreground mb-4">
          {{ t('live.calendar_dialog_hint') }}
        </p>

        <div
          v-if="loading"
          class="text-center py-4 text-[12px] text-muted-foreground"
        >
          {{ t('common.loading') }}
        </div>

        <div v-else-if="error" class="text-[12px] text-danger-600 mb-3">
          {{ error }}
        </div>

        <div v-else class="space-y-3">
          <code
            class="block bg-muted text-foreground rounded-md p-2.5 font-mono text-[11px] break-all border border-border"
          >
            {{ url }}
          </code>
          <div class="flex items-center gap-2">
            <UiButton size="sm" @click="copyUrl">
              {{ copied ? t('live.calendar_copied') : t('live.calendar_copy') }}
            </UiButton>
            <UiButton variant="outline" size="sm" @click="close">
              {{ t('common.close') }}
            </UiButton>
          </div>
          <p class="text-[11px] text-muted-foreground leading-relaxed">
            {{ t('live.calendar_paste_hint') }}
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
