<script setup lang="ts">
/**
 * Phase 5b.1 — Pre-join lobby.
 *
 * Foydalanuvchi `/app/live/:id` ga kirishdan oldin shu yerda:
 *  - Kamera/mikrofon preview (oddiy `getUserMedia` stream — LiveKit'ga ulanmagan)
 *  - Audio level meter (mikrofon kuchi vizual)
 *  - Device dropdowns (mic / cam / speaker)
 *  - Session info card (sarlavha, host, boshlanish vaqti, ishtirokchilar soni)
 *  - "Join now" tugmasi → /app/live/:id (haqiqiy LiveKit ulanish)
 *  - "Audio only" sekundar (kameragiz kuzatish)
 *
 * Cleanup: stream tracks unmount'da to'xtatiladi (browser camera LED o'chadi).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { liveSessionsApi } from '@shared/api/live'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'
import type { LiveSession } from '@shared/types/live'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const sessionId = computed(() => Number(route.params.id))

const session = ref<LiveSession | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const permissionError = ref<string | null>(null)

// Media state
const stream = ref<MediaStream | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)
const micEnabled = ref(true)
const camEnabled = ref(true)

// Devices
interface DeviceOption {
  value: string
  label: string
}
const audioInputs = ref<DeviceOption[]>([])
const videoInputs = ref<DeviceOption[]>([])
const audioOutputs = ref<DeviceOption[]>([])
const selectedMic = ref<string | null>(null)
const selectedCam = ref<string | null>(null)
const selectedSpeaker = ref<string | null>(null)

// Audio level (0–1)
const audioLevel = ref(0)
const audioContext = ref<AudioContext | null>(null)
const audioAnalyser = ref<AnalyserNode | null>(null)
let levelRafId: number | null = null

// Countdown
const now = ref(Date.now())
let nowTimer: ReturnType<typeof setInterval> | null = null

const startsInLabel = computed(() => {
  if (!session.value) return ''
  const start = new Date(session.value.scheduled_start).getTime()
  const diff = start - now.value
  if (diff <= 0) return t('live.lobby_starts_now')
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(mins / 60)
  if (hours >= 24) return `${Math.floor(hours / 24)} ${t('live.lobby_days')}`
  if (hours > 0) return `${hours}${t('live.lobby_h')} ${mins % 60}${t('live.lobby_m')}`
  return `${mins} ${t('live.lobby_min')}`
})

const isLive = computed(() => session.value?.status === 'live')
const isHost = computed(() => session.value?.host_user_id === auth.user?.id)

function fmtDateTime(s: string): string {
  try {
    return formatDate(s, locale.value, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return s
  }
}

async function loadSession() {
  loading.value = true
  error.value = null
  try {
    session.value = await liveSessionsApi.get(sessionId.value)
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'live-upcoming' })
      return
    }
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  try {
    const devs = await navigator.mediaDevices.enumerateDevices()
    audioInputs.value = devs
      .filter((d) => d.kind === 'audioinput')
      .map((d, i) => ({
        value: d.deviceId,
        label: d.label || `Mic ${i + 1}`,
      }))
    videoInputs.value = devs
      .filter((d) => d.kind === 'videoinput')
      .map((d, i) => ({
        value: d.deviceId,
        label: d.label || `Camera ${i + 1}`,
      }))
    audioOutputs.value = devs
      .filter((d) => d.kind === 'audiooutput')
      .map((d, i) => ({
        value: d.deviceId,
        label: d.label || `Speaker ${i + 1}`,
      }))
    if (!selectedMic.value && audioInputs.value[0]) {
      selectedMic.value = audioInputs.value[0].value
    }
    if (!selectedCam.value && videoInputs.value[0]) {
      selectedCam.value = videoInputs.value[0].value
    }
    if (!selectedSpeaker.value && audioOutputs.value[0]) {
      selectedSpeaker.value = audioOutputs.value[0].value
    }
  } catch (e) {
    console.warn('enumerateDevices failed', e)
  }
}

async function startPreview() {
  permissionError.value = null
  // Stop previous stream
  stopPreview()
  try {
    const constraints: MediaStreamConstraints = {
      audio: micEnabled.value
        ? selectedMic.value
          ? { deviceId: { exact: selectedMic.value } }
          : true
        : false,
      video: camEnabled.value
        ? selectedCam.value
          ? { deviceId: { exact: selectedCam.value }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { width: { ideal: 1280 }, height: { ideal: 720 } }
        : false,
    }
    if (!constraints.audio && !constraints.video) {
      // Hech nima yoqilmagan — preview yo'q
      return
    }
    const s = await navigator.mediaDevices.getUserMedia(constraints)
    stream.value = s
    // Refresh device labels (browser ruxsatdan keyin label'larni ko'rsatadi)
    await loadDevices()
    // Attach video
    if (videoRef.value && camEnabled.value) {
      videoRef.value.srcObject = s
    }
    // Audio level meter
    if (micEnabled.value && s.getAudioTracks().length > 0) {
      startAudioMeter(s)
    }
  } catch (e) {
    permissionError.value =
      e instanceof Error
        ? e.message
        : t('live.lobby_permission_denied_help')
  }
}

function stopPreview() {
  if (stream.value) {
    stream.value.getTracks().forEach((t) => t.stop())
    stream.value = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  stopAudioMeter()
}

function startAudioMeter(s: MediaStream) {
  try {
    const Ctx = window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext
    if (!Ctx) return
    audioContext.value = new Ctx()
    const source = audioContext.value.createMediaStreamSource(s)
    const analyser = audioContext.value.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)
    audioAnalyser.value = analyser
    const buf = new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount))
    const tick = () => {
      if (!audioAnalyser.value) return
      audioAnalyser.value.getByteTimeDomainData(buf as Uint8Array<ArrayBuffer>)
      // RMS
      let sum = 0
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128
        sum += v * v
      }
      const rms = Math.sqrt(sum / buf.length)
      audioLevel.value = Math.min(1, rms * 3)  // amplify
      levelRafId = requestAnimationFrame(tick)
    }
    tick()
  } catch (e) {
    console.warn('audio meter init failed', e)
  }
}

function stopAudioMeter() {
  if (levelRafId !== null) {
    cancelAnimationFrame(levelRafId)
    levelRafId = null
  }
  if (audioContext.value) {
    audioContext.value.close().catch(() => {})
    audioContext.value = null
  }
  audioAnalyser.value = null
  audioLevel.value = 0
}

// Audio level bars (5 ta)
const audioBars = computed(() => {
  const lv = audioLevel.value
  return [0.05, 0.2, 0.4, 0.6, 0.8].map((threshold) => lv > threshold)
})

function toggleMic() {
  micEnabled.value = !micEnabled.value
  startPreview()
}

function toggleCam() {
  camEnabled.value = !camEnabled.value
  startPreview()
}

watch([selectedMic, selectedCam], () => {
  if (stream.value) startPreview()
})

function goJoin() {
  // Preview stream'ni to'xtatamiz (LiveKit o'zi yangi stream ochadi)
  stopPreview()
  router.push({
    name: 'live-room',
    params: { id: sessionId.value },
  })
}

function goJoinAudioOnly() {
  stopPreview()
  router.push({
    name: 'live-room',
    params: { id: sessionId.value },
    query: { audio_only: '1' },
  })
}

function goBack() {
  router.back()
}

// Qurilma ulansa/uzilsa ro'yxatni yangilaymiz (hot-plug)
function onDeviceChange() {
  loadDevices().catch(() => null)
}

onMounted(async () => {
  await loadSession()
  await loadDevices()
  await startPreview()
  navigator.mediaDevices?.addEventListener?.('devicechange', onDeviceChange)
  nowTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onBeforeUnmount(() => {
  navigator.mediaDevices?.removeEventListener?.('devicechange', onDeviceChange)
  stopPreview()
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
})
</script>

<template>
  <UiBreadcrumb
    :items="[
      { label: t('dashboard.crumb_home'), to: '/app/dashboard' },
      auth.hasPermission('live.host')
        ? { label: t('live.title_host'), to: '/app/live' }
        : { label: t('live.title_student'), to: '/app/live/upcoming' },
      t('live.lobby_title'),
    ]"
    class="mb-6"
  />

  <div v-if="loading && !session" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <UiAlert v-else-if="error && !session" variant="danger">{{ error }}</UiAlert>

  <template v-else-if="session">
    <div class="mb-6">
      <h1 class="page-title mb-1.5">{{ t('live.lobby_title') }}</h1>
      <p class="page-subtitle">{{ t('live.lobby_subtitle') }}</p>
    </div>

    <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

    <!-- Permission help banner -->
    <UiAlert v-if="permissionError" variant="warning" class="mb-4">
      <strong>{{ t('live.lobby_permission_denied_title') }}</strong>
      <div class="text-[12px] mt-1">{{ t('live.lobby_permission_denied_help') }}</div>
      <UiButton variant="outline" size="sm" class="mt-2" @click="startPreview">
        {{ t('live.lobby_permission_retry') }}
      </UiButton>
    </UiAlert>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
      <!-- LEFT: video preview + controls -->
      <div>
        <!-- Video preview -->
        <div
          class="relative bg-[#0a0a0a] rounded-lg overflow-hidden border border-border"
          style="aspect-ratio: 16/9;"
        >
          <video
            v-show="camEnabled && !permissionError"
            ref="videoRef"
            autoplay
            playsinline
            muted
            class="w-full h-full object-cover"
            style="transform: scaleX(-1);"
          ></video>
          <div
            v-if="!camEnabled || permissionError"
            class="absolute inset-0 grid place-items-center text-white/60 font-mono text-[12px] uppercase tracking-widest"
          >
            <div class="flex flex-col items-center gap-3">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="6" width="13" height="12" rx="1" />
                <path d="M16 10l5-3v10l-5-3" />
                <path v-if="permissionError" d="M3 3l18 18" stroke-width="2" />
              </svg>
              <span>{{ permissionError ? t('live.lobby_camera_blocked') : t('live.lobby_camera_off') }}</span>
            </div>
          </div>

          <!-- Audio level bars (bottom-left) -->
          <div
            v-if="micEnabled && !permissionError"
            class="absolute bottom-4 left-4 flex items-end gap-1 h-8 bg-black/60 px-3 py-1.5 rounded-md"
          >
            <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="white" stroke-width="2">
              <rect x="6" y="2" width="6" height="10" rx="3" />
              <path d="M3 8a6 6 0 0 0 12 0M9 14v2" />
            </svg>
            <div
              v-for="(active, i) in audioBars"
              :key="i"
              class="w-1 rounded-sm transition-colors"
              :class="[
                active ? 'bg-success-400' : 'bg-white/20',
              ]"
              :style="{ height: `${4 + i * 3}px` }"
            ></div>
          </div>

          <!-- "You" label (top-right) -->
          <div
            class="absolute top-4 right-4 bg-black/60 text-white text-[11px] font-mono uppercase tracking-wider px-2 py-1 rounded"
          >
            {{ t('live.lobby_you') }}
          </div>
        </div>

        <!-- Toggle controls -->
        <div class="flex items-center gap-3 mt-4 flex-wrap">
          <button
            type="button"
            class="flex items-center gap-2 px-4 h-10 rounded-md text-[13px] font-medium border transition-colors"
            :class="
              micEnabled
                ? 'bg-foreground text-background border-foreground'
                : 'bg-danger-50 text-danger-700 border-danger-200 dark:bg-danger-700/15 dark:text-danger-200'
            "
            @click="toggleMic"
          >
            <svg width="16" height="16" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="2" width="6" height="10" rx="3" />
              <path d="M3 8a6 6 0 0 0 12 0M9 14v2" />
              <path v-if="!micEnabled" d="M2 2l14 14" />
            </svg>
            {{ micEnabled ? t('live.ctrl_mic') : t('live.lobby_mic_off') }}
          </button>
          <button
            type="button"
            class="flex items-center gap-2 px-4 h-10 rounded-md text-[13px] font-medium border transition-colors"
            :class="
              camEnabled
                ? 'bg-foreground text-background border-foreground'
                : 'bg-danger-50 text-danger-700 border-danger-200 dark:bg-danger-700/15 dark:text-danger-200'
            "
            @click="toggleCam"
          >
            <svg width="16" height="16" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="5" width="11" height="9" rx="1" />
              <path d="M13 8l3-2v7l-3-2" />
              <path v-if="!camEnabled" d="M2 2l14 14" />
            </svg>
            {{ camEnabled ? t('live.ctrl_cam') : t('live.lobby_cam_off') }}
          </button>
        </div>

        <!-- Device pickers -->
        <UiCard no-padding class="mt-5">
          <div class="px-5 py-3 border-b border-border">
            <span class="text-[13px] font-semibold">{{ t('live.lobby_devices') }}</span>
          </div>
          <div class="px-5 py-4 grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground block mb-1">
                {{ t('live.lobby_device_mic') }}
              </label>
              <UiSelect
                v-model="selectedMic"
                :options="audioInputs.length > 0 ? audioInputs : [{ value: '', label: t('live.lobby_device_none') }]"
                :placeholder="t('live.lobby_device_default')"
                :disabled="!micEnabled || audioInputs.length === 0"
              />
            </div>
            <div>
              <label class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground block mb-1">
                {{ t('live.lobby_device_cam') }}
              </label>
              <UiSelect
                v-model="selectedCam"
                :options="videoInputs.length > 0 ? videoInputs : [{ value: '', label: t('live.lobby_device_none') }]"
                :placeholder="t('live.lobby_device_default')"
                :disabled="!camEnabled || videoInputs.length === 0"
              />
            </div>
            <div>
              <label class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground block mb-1">
                {{ t('live.lobby_device_speaker') }}
              </label>
              <UiSelect
                v-model="selectedSpeaker"
                :options="audioOutputs.length > 0 ? audioOutputs : [{ value: '', label: t('live.lobby_device_none') }]"
                :placeholder="t('live.lobby_device_default')"
                :disabled="audioOutputs.length === 0"
              />
            </div>
          </div>
        </UiCard>
      </div>

      <!-- RIGHT: session info + join CTA (sticky) -->
      <aside class="space-y-4 lg:sticky lg:top-6 self-start">
        <UiCard no-padding>
          <div class="px-5 py-4">
            <div class="flex items-center gap-2 mb-3 flex-wrap">
              <UiBadge :variant="isLive ? 'success' : 'default'" with-dot>
                {{ isLive ? t('live.status_live') : t('live.status_scheduled') }}
              </UiBadge>
              <UiBadge v-if="isHost" variant="info">{{ t('live.lobby_role_host') }}</UiBadge>
            </div>
            <h2 class="text-[18px] font-semibold mb-2 leading-snug">
              {{ session.title }}
            </h2>
            <p
              v-if="session.description"
              class="text-[12.5px] text-muted-foreground leading-relaxed mb-3"
            >
              {{ session.description }}
            </p>
            <div class="text-[12px] space-y-1.5">
              <div class="flex justify-between gap-2">
                <span class="text-muted-foreground">{{ t('live.lobby_starts_in') }}:</span>
                <span class="font-mono font-semibold">{{ startsInLabel }}</span>
              </div>
              <div class="flex justify-between gap-2">
                <span class="text-muted-foreground">{{ t('live.lobby_start_at') }}:</span>
                <span class="font-mono">{{ fmtDateTime(session.scheduled_start) }}</span>
              </div>
              <div class="flex justify-between gap-2">
                <span class="text-muted-foreground">{{ t('live.lobby_duration') }}:</span>
                <span class="font-mono">{{ session.duration_minutes }} {{ t('live.lobby_min') }}</span>
              </div>
              <div v-if="session.is_recording_enabled" class="flex justify-between gap-2">
                <span class="text-muted-foreground">{{ t('live.lobby_recording') }}:</span>
                <span class="font-mono text-success-600">●</span>
              </div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-border space-y-2">
            <UiButton class="w-full justify-center" @click="goJoin">
              ▶ {{ isHost ? t('live.lobby_start_session') : t('live.lobby_join') }}
            </UiButton>
            <UiButton
              variant="outline"
              class="w-full justify-center"
              :disabled="!!permissionError"
              @click="goJoinAudioOnly"
            >
              🎧 {{ t('live.lobby_join_audio_only') }}
            </UiButton>
            <UiButton variant="ghost" class="w-full justify-center" @click="goBack">
              ← {{ t('common.cancel') }}
            </UiButton>
          </div>
        </UiCard>

        <UiCard no-padding>
          <div class="px-5 py-3 border-b border-border">
            <span class="text-[13px] font-semibold">{{ t('live.lobby_tips_title') }}</span>
          </div>
          <ul class="px-5 py-3 text-[12px] text-muted-foreground space-y-1.5 list-disc list-inside">
            <li>{{ t('live.lobby_tip_quiet') }}</li>
            <li>{{ t('live.lobby_tip_headphones') }}</li>
            <li>{{ t('live.lobby_tip_camera') }}</li>
          </ul>
        </UiCard>
      </aside>
    </div>
  </template>
</template>
