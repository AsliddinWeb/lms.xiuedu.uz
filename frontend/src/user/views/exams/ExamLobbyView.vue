<script setup lang="ts">
/**
 * Phase 6d — Exam Lobby.
 *
 * Talaba imtihonni boshlashdan oldin:
 *  - Imtihon haqida ma'lumot (sarlavha, davomiyligi, savol soni, urinishlar)
 *  - System check (kamera / mikrofon / screen share / Internet)
 *  - ID photo capture (yuz rasm — Phase 6f'da face-api bilan match qilinadi)
 *  - Proctoring rozilik
 *  - Tabni yopiq tutish ogohlantirishi
 *
 * "Boshlash" tugmasi faqat barcha checklar yashil bo'lganda aktiv.
 * Bosilgach: POST /exams/:id/start → router push /app/exams/:id/take.
 */

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import { attemptsApi, examsApi } from '@shared/api/exams'
import { proctoringApi } from '@shared/api/proctoring'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import type { Exam } from '@shared/types/exams'
import { useFaceDetection } from '@user/composables/useFaceDetection'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const examId = computed(() => Number(route.params.id))
const exam = ref<Exam | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const starting = ref(false)

// --- Media state ---
const cameraStream = ref<MediaStream | null>(null)
const screenStream = ref<MediaStream | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)
const idPhotoCanvasRef = ref<HTMLCanvasElement | null>(null)
const idPhotoDataUrl = ref<string | null>(null)

// --- Check state ---
const cameraOk = ref(false)
const micOk = ref(false)
const screenOk = ref(false)
const onlineOk = ref(navigator.onLine)
const photoOk = computed(() => idPhotoDataUrl.value !== null)
const consentOk = ref(false)

// --- Internet listener ---
function onOnline() {
  onlineOk.value = true
}
function onOffline() {
  onlineOk.value = false
}

// --- Computed: is all required checks green? ---
const allChecksGreen = computed(() => {
  if (!exam.value) return false
  if (!onlineOk.value) return false
  if (!consentOk.value) return false
  // Photo always required for proctoring exams
  if (exam.value.proctoring_enabled && !photoOk.value) return false
  if (exam.value.proctoring_enabled) {
    if (!cameraOk.value) return false
    if (exam.value.require_face_id && !micOk.value) return false
    if (exam.value.require_screen_share && !screenOk.value) return false
  }
  return true
})

async function loadExam() {
  loading.value = true
  error.value = null
  try {
    exam.value = await examsApi.get(examId.value)
    if (exam.value.status !== 'published') {
      error.value = t('exam_lobby.error_not_published')
    }
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'dashboard' })
      return
    }
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function requestCameraMic() {
  try {
    const needsMic = exam.value?.require_face_id ?? false
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 } },
      audio: needsMic,
    })
    cameraStream.value = stream
    cameraOk.value = stream.getVideoTracks().length > 0
    micOk.value = needsMic ? stream.getAudioTracks().length > 0 : true
    if (videoRef.value) {
      videoRef.value.srcObject = stream
    }
  } catch (e) {
    cameraOk.value = false
    micOk.value = false
    error.value = t('exam_lobby.error_camera_blocked')
    console.warn('camera permission denied', e)
  }
}

async function requestScreenShare() {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: { displaySurface: 'monitor' } as MediaTrackConstraints,
      audio: false,
    })
    screenStream.value = stream
    screenOk.value = true
    // Track ended event — if user stops sharing
    stream.getVideoTracks()[0].addEventListener('ended', () => {
      screenOk.value = false
      screenStream.value = null
    })
  } catch (e) {
    screenOk.value = false
    console.warn('screen share denied', e)
  }
}

const faceDetection = useFaceDetection()
const idPhotoNoFace = ref(false)

async function captureIdPhoto() {
  if (!videoRef.value || !idPhotoCanvasRef.value) return
  const v = videoRef.value
  const c = idPhotoCanvasRef.value
  c.width = v.videoWidth || 640
  c.height = v.videoHeight || 480
  const ctx = c.getContext('2d')
  if (!ctx) return
  ctx.drawImage(v, 0, 0, c.width, c.height)
  idPhotoDataUrl.value = c.toDataURL('image/jpeg', 0.85)
  idPhotoNoFace.value = false

  // Phase 9a — face descriptor'ni ham olib qo'yamiz (exam taking view'da ishlatamiz)
  try {
    await faceDetection.loadModels()
    const result = await faceDetection.detectWithDescriptor(c)
    if (!result.descriptor || result.faceCount !== 1) {
      idPhotoNoFace.value = true
      return
    }
    sessionStorage.setItem(
      `exam_face_ref_${examId.value}`,
      JSON.stringify(faceDetection.descriptorToJSON(result.descriptor)),
    )
  } catch (e) {
    console.warn('face descriptor extraction failed', e)
  }
}

function retakeIdPhoto() {
  idPhotoDataUrl.value = null
}

function stopAllStreams() {
  cameraStream.value?.getTracks().forEach((t) => t.stop())
  cameraStream.value = null
  screenStream.value?.getTracks().forEach((t) => t.stop())
  screenStream.value = null
  if (videoRef.value) videoRef.value.srcObject = null
}

function dataUrlToBlob(dataUrl: string): Blob {
  const [meta, base64] = dataUrl.split(',')
  const mime = /:(.*?);/.exec(meta)?.[1] ?? 'image/jpeg'
  const bin = atob(base64)
  const arr = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
  return new Blob([arr], { type: mime })
}

async function handleStart() {
  if (!allChecksGreen.value || !exam.value) return
  starting.value = true
  error.value = null
  try {
    const attempt = await attemptsApi.start(exam.value.id)
    // Proctoring yoqilgan bo'lsa, ID rasmni serverga yuborish
    if (exam.value.proctoring_enabled && idPhotoDataUrl.value) {
      try {
        const blob = dataUrlToBlob(idPhotoDataUrl.value)
        await proctoringApi.uploadIdReference(attempt.id, blob)
      } catch (e) {
        console.warn('id reference upload failed', e)
        // davom etamiz — proctoring kelajakda qayta urinib ko'rishi mumkin
      }
    }
    // Streamlarni saqlab qolamiz (taking page'da qayta ishlatamiz) —
    // hozircha to'xtatamiz, take view o'z permission'larini qayta so'raydi.
    stopAllStreams()
    router.replace({
      name: 'exam-take',
      params: { id: String(exam.value.id), attemptId: String(attempt.id) },
    })
  } catch (e) {
    error.value = extractErrorMessage(e, t('exam_lobby.error_start_failed'))
  } finally {
    starting.value = false
  }
}

onMounted(() => {
  loadExam()
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
})

onBeforeUnmount(() => {
  stopAllStreams()
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
})

watch(
  () => exam.value,
  (e) => {
    // Avtomatik kamera so'rash agar proctoring yoqilgan bo'lsa
    if (e && e.proctoring_enabled && !cameraStream.value) {
      requestCameraMic()
    }
  },
)
</script>

<template>
  <div v-if="loading && !exam" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !exam" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="exam">
    <UiBreadcrumb
      :items="[t('dashboard.crumb_home'), t('exams.tab_exams'), exam.title]"
      class="mb-6"
    />

    <div class="mb-6">
      <div class="flex items-center gap-2 mb-2 flex-wrap">
        <UiBadge variant="default">{{ t(`exams.type_${exam.type}`) }}</UiBadge>
        <UiBadge v-if="exam.proctoring_enabled" variant="warning" with-dot>
          {{ t('exam_lobby.proctoring_required') }}
        </UiBadge>
      </div>
      <h1 class="page-title mb-1.5">{{ exam.title }}</h1>
      <p v-if="exam.description" class="page-subtitle">{{ exam.description }}</p>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
      <!-- Left: camera + checks -->
      <div class="space-y-4">
        <!-- Camera preview / ID photo -->
        <UiCard v-if="exam.proctoring_enabled">
          <template #header>
            <div class="text-[13px] font-semibold">{{ t('exam_lobby.section_id_photo') }}</div>
          </template>

          <div class="space-y-3">
            <div class="aspect-video bg-black rounded-md overflow-hidden relative">
              <video
                v-show="!idPhotoDataUrl"
                ref="videoRef"
                autoplay
                muted
                playsinline
                class="w-full h-full object-cover"
              ></video>
              <img
                v-if="idPhotoDataUrl"
                :src="idPhotoDataUrl"
                class="w-full h-full object-cover"
                :alt="t('exam_lobby.id_photo_alt')"
              />
              <canvas ref="idPhotoCanvasRef" class="hidden"></canvas>

              <div
                v-if="!cameraStream && !idPhotoDataUrl"
                class="absolute inset-0 grid place-items-center text-muted-foreground text-[12px]"
              >
                {{ t('exam_lobby.camera_off') }}
              </div>
            </div>

            <p class="text-[12px] text-muted-foreground">
              {{ t('exam_lobby.id_photo_hint') }}
            </p>

            <UiAlert v-if="idPhotoNoFace" variant="warning" class="text-[12px]">
              {{ t('exam_lobby.id_photo_no_face') }}
            </UiAlert>

            <div class="flex flex-wrap gap-2">
              <UiButton
                v-if="!cameraStream"
                variant="outline"
                size="sm"
                @click="requestCameraMic"
              >
                {{ t('exam_lobby.start_camera') }}
              </UiButton>
              <UiButton
                v-if="cameraStream && !idPhotoDataUrl"
                size="sm"
                @click="captureIdPhoto"
              >
                {{ t('exam_lobby.capture_photo') }}
              </UiButton>
              <UiButton v-if="idPhotoDataUrl" variant="ghost" size="sm" @click="retakeIdPhoto">
                {{ t('exam_lobby.retake_photo') }}
              </UiButton>
            </div>
          </div>
        </UiCard>

        <!-- System checklist -->
        <UiCard>
          <template #header>
            <div class="text-[13px] font-semibold">{{ t('exam_lobby.section_system_check') }}</div>
          </template>

          <ul class="space-y-2 text-[13px]">
            <li class="flex items-center justify-between">
              <span class="flex items-center gap-2">
                <span
                  class="inline-block w-2 h-2 rounded-full"
                  :class="onlineOk ? 'bg-success-500' : 'bg-danger-500'"
                ></span>
                {{ t('exam_lobby.check_internet') }}
              </span>
              <span class="text-[11px] font-mono text-muted-foreground">
                {{ onlineOk ? t('exam_lobby.ok') : t('exam_lobby.offline') }}
              </span>
            </li>

            <li v-if="exam.proctoring_enabled" class="flex items-center justify-between">
              <span class="flex items-center gap-2">
                <span
                  class="inline-block w-2 h-2 rounded-full"
                  :class="cameraOk ? 'bg-success-500' : 'bg-danger-500'"
                ></span>
                {{ t('exam_lobby.check_camera') }}
              </span>
              <UiButton
                v-if="!cameraOk"
                variant="ghost"
                size="sm"
                @click="requestCameraMic"
              >
                {{ t('exam_lobby.grant') }}
              </UiButton>
              <span v-else class="text-[11px] font-mono text-muted-foreground">{{ t('exam_lobby.ok') }}</span>
            </li>

            <li
              v-if="exam.proctoring_enabled && exam.require_face_id"
              class="flex items-center justify-between"
            >
              <span class="flex items-center gap-2">
                <span
                  class="inline-block w-2 h-2 rounded-full"
                  :class="micOk ? 'bg-success-500' : 'bg-danger-500'"
                ></span>
                {{ t('exam_lobby.check_mic') }}
              </span>
              <span class="text-[11px] font-mono text-muted-foreground">
                {{ micOk ? t('exam_lobby.ok') : t('exam_lobby.not_granted') }}
              </span>
            </li>

            <li
              v-if="exam.proctoring_enabled && exam.require_screen_share"
              class="flex items-center justify-between"
            >
              <span class="flex items-center gap-2">
                <span
                  class="inline-block w-2 h-2 rounded-full"
                  :class="screenOk ? 'bg-success-500' : 'bg-danger-500'"
                ></span>
                {{ t('exam_lobby.check_screen') }}
              </span>
              <UiButton
                v-if="!screenOk"
                variant="ghost"
                size="sm"
                @click="requestScreenShare"
              >
                {{ t('exam_lobby.grant') }}
              </UiButton>
              <span v-else class="text-[11px] font-mono text-muted-foreground">{{ t('exam_lobby.ok') }}</span>
            </li>

            <li v-if="exam.proctoring_enabled" class="flex items-center justify-between">
              <span class="flex items-center gap-2">
                <span
                  class="inline-block w-2 h-2 rounded-full"
                  :class="photoOk ? 'bg-success-500' : 'bg-warning-500'"
                ></span>
                {{ t('exam_lobby.check_photo') }}
              </span>
              <span class="text-[11px] font-mono text-muted-foreground">
                {{ photoOk ? t('exam_lobby.ok') : t('exam_lobby.required') }}
              </span>
            </li>
          </ul>
        </UiCard>

        <!-- Consent -->
        <UiCard>
          <template #header>
            <div class="text-[13px] font-semibold">{{ t('exam_lobby.section_consent') }}</div>
          </template>

          <ul class="text-[12px] text-muted-foreground space-y-1.5 list-disc pl-5 mb-3">
            <li>{{ t('exam_lobby.consent_item_1') }}</li>
            <li v-if="exam.proctoring_enabled">{{ t('exam_lobby.consent_item_2') }}</li>
            <li v-if="!exam.allow_tab_switch">{{ t('exam_lobby.consent_item_3') }}</li>
            <li>{{ t('exam_lobby.consent_item_4') }}</li>
          </ul>

          <label class="flex items-start gap-2 text-[13px] cursor-pointer">
            <input v-model="consentOk" type="checkbox" class="mt-0.5" />
            <span>{{ t('exam_lobby.consent_label') }}</span>
          </label>
        </UiCard>
      </div>

      <!-- Right: info + start button -->
      <UiCard>
        <template #header>
          <div class="text-[13px] font-semibold">{{ t('exam_lobby.section_info') }}</div>
        </template>

        <dl class="text-[13px] space-y-2 mb-4">
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('exam_lobby.info_duration') }}</dt>
            <dd class="font-mono">{{ exam.duration_minutes }} {{ t('exam_lobby.minutes') }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('exam_lobby.info_questions') }}</dt>
            <dd class="font-mono">{{ exam.question_count ?? '—' }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('exam_lobby.info_max_attempts') }}</dt>
            <dd class="font-mono">{{ exam.max_attempts }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('exam_lobby.info_passing_score') }}</dt>
            <dd class="font-mono">{{ exam.passing_score }}%</dd>
          </div>
          <div v-if="exam.available_until" class="flex justify-between gap-3">
            <dt class="text-muted-foreground">{{ t('exam_lobby.info_available_until') }}</dt>
            <dd class="font-mono">
              {{ new Date(exam.available_until).toLocaleString() }}
            </dd>
          </div>
        </dl>

        <UiAlert v-if="!exam.allow_tab_switch" variant="warning" class="mb-3">
          <div class="text-[12px]">{{ t('exam_lobby.warning_tab_switch') }}</div>
        </UiAlert>

        <UiButton
          class="w-full"
          :disabled="!allChecksGreen || starting"
          :loading="starting"
          @click="handleStart"
        >
          {{ t('exam_lobby.start_exam') }} →
        </UiButton>

        <p
          v-if="!allChecksGreen"
          class="text-[11px] text-muted-foreground mt-2 text-center"
        >
          {{ t('exam_lobby.complete_checks_first') }}
        </p>
      </UiCard>
    </div>
  </template>
</template>
