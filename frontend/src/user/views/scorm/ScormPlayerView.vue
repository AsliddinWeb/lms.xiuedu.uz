<script setup lang="ts">
/**
 * SCORM Player — Phase 11a.
 *
 * Talaba lesson ichidan SCORM kursni o'tadi:
 *   1. `start(package_id, lesson_id)` chaqirib attempt yaratadi/davom etadi
 *   2. `useScormApi` bridge'ni o'rnatadi (window.API + window.API_1484_11)
 *   3. SCORM content iframe ichida yuklanadi (launch_full_url)
 *   4. Iframe content `parent.API.LMSGetValue`/`LMSSetValue`/etc. chaqiradi
 *   5. Bridge backend'ga commit qiladi (har 30s + LMSCommit/LMSFinish'da)
 *   6. Talaba sahifadan chiqsa, beforeunload'da finish chaqiriladi
 */

import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import type { ScormAttempt, ScormPackage } from '@shared/api/scorm'
import { scormApi } from '@shared/api/scorm'
import { extractErrorMessage } from '@shared/api/client'
import { useScormApi } from '@user/composables/useScormApi'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const packageId = ref<number>(Number(route.params.packageId))
const lessonId = ref<number | null>(
  route.query.lesson_id ? Number(route.query.lesson_id) : null,
)

const loading = ref(true)
const error = ref<string | null>(null)
const launchUrl = ref<string>('')
const attempt = ref<ScormAttempt | null>(null)
const pkg = ref<ScormPackage | null>(null)

let bridge: ReturnType<typeof useScormApi> | null = null

async function load() {
  loading.value = true
  error.value = null
  try {
    const resp = await scormApi.start(packageId.value, lessonId.value ?? undefined)
    attempt.value = resp.attempt
    pkg.value = resp.package
    launchUrl.value = resp.launch_full_url

    // Bridge'ni install qilamiz IFRAME yuklanishidan oldin
    bridge = useScormApi({
      attemptId: resp.attempt.id,
      initialCmi: () => (resp.attempt.cmi_data as Record<string, unknown>) ?? {},
    })
    bridge.install()
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function exitCourse() {
  if (bridge) {
    await bridge.finish()
  }
  // Lesson sahifasiga qaytish
  if (lessonId.value) {
    router.back()
  } else {
    router.push('/app/learning')
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  // Yakuniy commit (best-effort, async natija kerak emas)
  if (bridge && bridge.isInitialized()) {
    void bridge.commit()
    // Browser standart confirmation
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  void load()
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  if (bridge) {
    void bridge.finish()
    bridge.uninstall()
    bridge = null
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-background border-b border-border px-6 py-3 flex items-center gap-4">
      <div class="flex-1">
        <div class="mono-tag mb-0.5">{{ t('scorm.player_tag') }}</div>
        <h1 class="text-[15px] font-semibold truncate">
          {{ pkg?.title || t('scorm.loading_title') }}
        </h1>
      </div>
      <UiButton variant="outline" size="sm" @click="exitCourse">
        ← {{ t('scorm.exit') }}
      </UiButton>
    </header>

    <!-- Body -->
    <div class="flex-1 bg-muted/30 relative">
      <div v-if="loading" class="p-8">
        <UiSkeleton :count="3" />
      </div>

      <UiAlert v-else-if="error" variant="danger" class="m-6">{{ error }}</UiAlert>

      <iframe
        v-else-if="launchUrl"
        :src="launchUrl"
        class="absolute inset-0 w-full h-full border-0 bg-white"
        :title="pkg?.title || 'SCORM content'"
        allow="autoplay; fullscreen"
      />
    </div>

    <!-- Footer status -->
    <footer
      v-if="attempt"
      class="bg-background border-t border-border px-6 py-2 flex items-center gap-4 text-[12px] text-muted-foreground"
    >
      <span>{{ t('scorm.attempt_label', { n: attempt.attempt_number }) }}</span>
      <span class="font-mono">{{ t(`scorm.status_${attempt.status}`) }}</span>
      <span v-if="attempt.score_raw" class="font-mono ml-auto">
        {{ t('scorm.score') }}: {{ attempt.score_raw }}
      </span>
    </footer>
  </div>
</template>
