<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import NativeRoom, {
  type ChatMessage,
  type HandRaiseEvent,
  type ParticipantState,
  type QaEvent,
  type ReactionEvent,
} from '@shared/components/live/NativeRoom.vue'
import { liveCaptionsApi, liveSessionsApi, type LiveCaptionItem } from '@shared/api/live'
import { useLiveRecorder } from '@user/composables/useLiveRecorder'
import { useSpeechRecognition, type CaptionSegment } from '@user/composables/useSpeechRecognition'
import { extractErrorMessage, isNotFound } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { useAuthStore } from '@shared/stores/auth'
import type {
  AttendanceSummary,
  LiveAdmissionItem,
  LiveAttendanceItem,
  LiveJoinInfo,
  LiveSession,
  LiveStatus,
} from '@shared/types/live'

import RecordingUploader from '@user/components/live/RecordingUploader.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const sessionId = computed(() => Number(route.params.id))

// Phase 5b.9 — Audio-only mode (lobby'dan ?audio_only=1 query bilan kelganda)
const audioOnly = computed(() => route.query.audio_only === '1')

// Phase 5b.9 — Permission denied state
const permissionDenied = ref(false)
const retryingPermission = ref(false)

function isPermissionError(msg: string): boolean {
  const m = msg.toLowerCase()
  return (
    m.includes('permission denied') ||
    m.includes('notallowederror') ||
    m.includes('permission') ||
    m.includes('notreadableerror') ||
    m.includes('not allowed')
  )
}

async function retryPermissions(includeCamera = true) {
  retryingPermission.value = true
  try {
    const ok = await nativeRoomRef.value?.retryPermissions(includeCamera)
    if (ok) {
      permissionDenied.value = false
      error.value = null
    }
  } finally {
    retryingPermission.value = false
  }
}

function dismissPermissionBanner() {
  permissionDenied.value = false
}

const session = ref<LiveSession | null>(null)
const joinInfo = ref<LiveJoinInfo | null>(null)
const attendance = ref<LiveAttendanceItem[]>([])
const summary = ref<AttendanceSummary | null>(null)
const recomputing = ref(false)

const loading = ref(false)
const error = ref<string | null>(null)
const transitioning = ref(false)
const joinedRoom = ref(false)

// Tabs & chat
type Tab = 'chat' | 'people' | 'qa'
const activeTab = ref<Tab>('chat')

// Phase 5b.8 / 55.7 — Mobile drawer state (side panel).
// Desktop (>1024px): panel doimiy ustun sifatida ochiq.
// Mobil/planshet (<=1024px): drawer YOPIQ boshlanadi — aks holda chat paneli
// butun ekranni qoplab video ko'rinmasdi ("telefonda faqat chat" bug'i).
const panelOpen = ref(
  typeof window !== 'undefined' ? window.innerWidth > 1024 : true,
)
function togglePanel() {
  panelOpen.value = !panelOpen.value
}
function closePanel() {
  panelOpen.value = false
}
const chatInput = ref('')
const chatLog = ref<ChatMessage[]>([])
const chatLogRef = ref<HTMLDivElement | null>(null)

// LiveKit state
const participants = ref<ParticipantState[]>([])
const audioMuted = ref(false)
const videoMuted = ref(false)
const screenSharing = ref(false)
// Phase 55.4 — talaba ekran ulasha oladimi (host ruxsati). Host doim true.
const screenAllowed = ref(true)
const connQuality = ref<'excellent' | 'good' | 'poor' | 'unknown'>('unknown')
const roomConnected = ref(false)


// Phase 5b.7 — Background blur state
const backgroundBlurEnabled = ref(false)
const backgroundBlurLoading = ref(false)

async function toggleBackgroundBlur() {
  if (backgroundBlurLoading.value) return
  backgroundBlurLoading.value = true
  try {
    if (backgroundBlurEnabled.value) {
      await nativeRoomRef.value?.disableBackgroundBlur()
      backgroundBlurEnabled.value = false
    } else {
      await nativeRoomRef.value?.enableBackgroundBlur(10)
      backgroundBlurEnabled.value = true
    }
  } finally {
    backgroundBlurLoading.value = false
  }
}

// Phase 5b.6 — Reactions + hand raise
const REACTION_EMOJIS = ['👏', '👍', '❤️', '😂', '🎉'] as const

interface FloatingReaction {
  id: number
  emoji: string
  nick: string
  startX: number  // % chap
}
const floatingReactions = ref<FloatingReaction[]>([])
let floatingReactionSeq = 0

function onReaction(data: ReactionEvent) {
  floatingReactionSeq++
  const id = floatingReactionSeq
  floatingReactions.value = [
    ...floatingReactions.value,
    {
      id,
      emoji: data.emoji,
      nick: data.nick,
      startX: 5 + Math.random() * 80,  // 5-85%
    },
  ]
  // 4s keyin avtomatik o'chirish
  setTimeout(() => {
    floatingReactions.value = floatingReactions.value.filter((r) => r.id !== id)
  }, 4000)
}

const handRaisedIds = ref<Set<string>>(new Set())
const myHandRaised = ref(false)

function onHandRaise(data: HandRaiseEvent) {
  const next = new Set(handRaisedIds.value)
  if (data.up) next.add(data.from)
  else next.delete(data.from)
  handRaisedIds.value = next
}

const handRaisedCount = computed(() => handRaisedIds.value.size)

const showReactionPicker = ref(false)

async function sendReaction(emoji: string) {
  await nativeRoomRef.value?.sendReaction(emoji)
  showReactionPicker.value = false
}

async function toggleHandRaise() {
  const next = !myHandRaised.value
  myHandRaised.value = next
  await nativeRoomRef.value?.sendHandRaise(next)
}

// ============================================================================
// Phase 55.6 — Q&A (data-channel orqali, jonli)
// ============================================================================
interface QaQuestion {
  id: string
  from: string
  nick: string
  text: string
  votes: number
  answered: boolean
  ts: number
  voters: Set<string>
}
const questions = ref<QaQuestion[]>([])
const qaInput = ref('')

// Ovoz bo'yicha, javoblanmaganlar yuqorida
const sortedQuestions = computed(() =>
  [...questions.value].sort((a, b) => {
    if (a.answered !== b.answered) return a.answered ? 1 : -1
    if (b.votes !== a.votes) return b.votes - a.votes
    return a.ts - b.ts
  }),
)
const myIdentity = computed(() => String(auth.user?.id ?? ''))

function applyQa(e: QaEvent) {
  if (e.action === 'ask' && e.text) {
    if (questions.value.some((q) => q.id === e.id)) return
    questions.value.push({
      id: e.id,
      from: e.from,
      nick: e.nick,
      text: e.text,
      votes: 0,
      answered: false,
      ts: e.ts,
      voters: new Set(),
    })
  } else if (e.action === 'upvote') {
    const q = questions.value.find((x) => x.id === e.id)
    if (q && !q.voters.has(e.from)) {
      q.voters.add(e.from)
      q.votes = q.voters.size
    }
  } else if (e.action === 'answer') {
    const q = questions.value.find((x) => x.id === e.id)
    if (q) q.answered = true
  }
}
function onQa(data: QaEvent) {
  applyQa(data)
}
async function askQuestion() {
  const text = qaInput.value.trim()
  if (!text) return
  const id = `${myIdentity.value}-${Date.now()}-${Math.floor(Math.random() * 1000)}`
  const ev: QaEvent = { action: 'ask', id, text, from: myIdentity.value, nick: auth.user?.full_name ?? 'Siz', ts: Date.now() }
  applyQa(ev)
  qaInput.value = ''
  await nativeRoomRef.value?.sendQa({ action: 'ask', id, text })
}
async function upvoteQuestion(id: string) {
  applyQa({ action: 'upvote', id, from: myIdentity.value, nick: '', ts: Date.now() })
  await nativeRoomRef.value?.sendQa({ action: 'upvote', id })
}
async function answerQuestion(id: string) {
  applyQa({ action: 'answer', id, from: myIdentity.value, nick: '', ts: Date.now() })
  await nativeRoomRef.value?.sendQa({ action: 'answer', id })
}
const unansweredCount = computed(() => questions.value.filter((q) => !q.answered).length)

// Phase 5b.3 — Local mic audio level (0-1)
const localAudioLevel = ref(0)
const audioLevelBars = computed(() => {
  const lv = localAudioLevel.value
  return [0.05, 0.2, 0.4, 0.6, 0.8].map((threshold) => lv > threshold)
})
function onAudioLevel(level: number) {
  localAudioLevel.value = level
}

// Phase 5b.2 — In-room device selector
interface DeviceOption { value: string; label: string }
const audioInputs = ref<DeviceOption[]>([])
const videoInputs = ref<DeviceOption[]>([])
const audioOutputs = ref<DeviceOption[]>([])
const currentMicId = ref<string>('')
const currentCamId = ref<string>('')
const currentSpeakerId = ref<string>('')

async function loadDevices() {
  try {
    const devs = await navigator.mediaDevices.enumerateDevices()
    audioInputs.value = devs
      .filter((d) => d.kind === 'audioinput')
      .map((d, i) => ({ value: d.deviceId, label: d.label || `Mic ${i + 1}` }))
    videoInputs.value = devs
      .filter((d) => d.kind === 'videoinput')
      .map((d, i) => ({ value: d.deviceId, label: d.label || `Camera ${i + 1}` }))
    audioOutputs.value = devs
      .filter((d) => d.kind === 'audiooutput')
      .map((d, i) => ({ value: d.deviceId, label: d.label || `Speaker ${i + 1}` }))
    if (!currentMicId.value && audioInputs.value[0]) {
      currentMicId.value = audioInputs.value[0].value
    }
    if (!currentCamId.value && videoInputs.value[0]) {
      currentCamId.value = videoInputs.value[0].value
    }
    if (!currentSpeakerId.value && audioOutputs.value[0]) {
      currentSpeakerId.value = audioOutputs.value[0].value
    }
  } catch (e) {
    console.warn('enumerateDevices failed', e)
  }
}

async function switchMic(deviceId: string) {
  if (deviceId === currentMicId.value) return
  await nativeRoomRef.value?.switchAudioInput(deviceId)
  currentMicId.value = deviceId
}
async function switchCam(deviceId: string) {
  if (deviceId === currentCamId.value) return
  await nativeRoomRef.value?.switchVideoInput(deviceId)
  currentCamId.value = deviceId
}
async function switchSpeaker(deviceId: string) {
  if (deviceId === currentSpeakerId.value) return
  await nativeRoomRef.value?.switchAudioOutput(deviceId)
  currentSpeakerId.value = deviceId
}

const elapsedSeconds = ref(0)
let elapsedTimer: ReturnType<typeof setInterval> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

const nativeRoomRef = ref<InstanceType<typeof NativeRoom> | null>(null)
const mainVideoRef = ref<HTMLVideoElement | null>(null)
const mainAudioRef = ref<HTMLAudioElement | null>(null)
const thumbRefs = ref<Record<string, HTMLVideoElement | null>>({})

const isHost = computed(() => session.value?.host_user_id === auth.user?.id)
const isPlatformAdmin = computed(() =>
  auth.permissions.some((p) => p === 'platform.*'),
)
const canManage = computed(() => isHost.value || isPlatformAdmin.value)

// === Waiting room (admission) — Phase 31 ===
const admissionPending = computed(() => joinInfo.value?.pending === true)
const pendingAdmissions = ref<LiveAdmissionItem[]>([])
let admissionPollTimer: ReturnType<typeof setInterval> | null = null
let hostAdmissionTimer: ReturnType<typeof setInterval> | null = null

// Talaba: tasdiq kelguncha join-info'ni qayta so'raymiz
function startAdmissionPoll() {
  if (admissionPollTimer) return
  admissionPollTimer = setInterval(async () => {
    try {
      joinInfo.value = await liveSessionsApi.getJoinInfo(sessionId.value)
      if (!admissionPending.value && admissionPollTimer) {
        clearInterval(admissionPollTimer)
        admissionPollTimer = null
      }
    } catch {
      // ignore
    }
  }, 4000)
}

// Host: kutayotgan so'rovlarni davriy yuklaymiz
async function refreshAdmissions() {
  try {
    pendingAdmissions.value = await liveSessionsApi.listAdmissions(sessionId.value)
  } catch {
    pendingAdmissions.value = []
  }
}
function startHostAdmissionPoll() {
  if (hostAdmissionTimer) return
  refreshAdmissions()
  hostAdmissionTimer = setInterval(refreshAdmissions, 5000)
}
async function decideAdmission(userId: number, approve: boolean) {
  try {
    await liveSessionsApi.decideAdmission(sessionId.value, userId, approve)
    pendingAdmissions.value = pendingAdmissions.value.filter(
      (a) => a.user_id !== userId,
    )
  } catch (e) {
    setTransientError(extractErrorMessage(e, t('common.save_error')))
  }
}

const liveKitUrl = computed<string>(() => {
  const cfg = joinInfo.value?.embed_config
  if (cfg && typeof cfg.url === 'string') return cfg.url
  return joinInfo.value?.join_url ?? ''
})

const participantCount = computed(() => participants.value.length)

// Asosiy speaker (eng katta video): screen sharing bo'lsa shu;
// aks holda eng birinchi gapirayotgan; bo'lmasa local user (host) yoki birinchi remote.
const mainParticipant = computed<ParticipantState | null>(() => {
  if (participants.value.length === 0) return null
  const screenShare = participants.value.find((p) => p.isScreenSharing)
  if (screenShare) return screenShare
  const speaking = participants.value.find((p) => p.isSpeaking && !p.videoMuted)
  if (speaking) return speaking
  const host = participants.value.find((p) => p.isHost && !p.videoMuted)
  if (host) return host
  const anyVideo = participants.value.find((p) => !p.videoMuted)
  if (anyVideo) return anyVideo
  return participants.value[0]
})

const thumbnailParticipants = computed<ParticipantState[]>(() =>
  participants.value
    .filter((p) => p.identity !== mainParticipant.value?.identity)
    .slice(0, 5),
)

const extraCount = computed(() =>
  Math.max(0, participants.value.length - 1 - thumbnailParticipants.value.length),
)

const formattedElapsed = computed(() => {
  const h = Math.floor(elapsedSeconds.value / 3600)
  const m = Math.floor((elapsedSeconds.value % 3600) / 60)
  const s = elapsedSeconds.value % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const qualityLabel = computed(() => {
  if (connQuality.value === 'excellent') return t('live.quality_excellent')
  if (connQuality.value === 'good') return t('live.quality_good')
  if (connQuality.value === 'poor') return t('live.quality_poor')
  return '—'
})

const qualityClass = computed(() => {
  if (connQuality.value === 'excellent' || connQuality.value === 'good') return 'good'
  if (connQuality.value === 'poor') return 'poor'
  return ''
})

// Phase 5b.5 — Network quality bar (signal bars + resolution + RTT)
const signalBars = computed(() => {
  // 4 ta bar — excellent=4, good=3, poor=2, unknown=0
  if (connQuality.value === 'excellent') return 4
  if (connQuality.value === 'good') return 3
  if (connQuality.value === 'poor') return 2
  return 0
})

const videoResolution = ref<{ width?: number; height?: number } | null>(null)
const connRtt = ref<number | null>(null)
let qualityPollTimer: ReturnType<typeof setInterval> | null = null

function pollQualityStats() {
  // Resolution: NativeRoom orqali olamiz. RTT esa real WebRTC stats orqali
  // NativeRoom'dan `@rtt` event bilan keladi (onRtt).
  const settings = nativeRoomRef.value?.getLocalVideoSettings?.()
  videoResolution.value = settings ?? null
}

function onRtt(ms: number | null) {
  connRtt.value = ms
}

const resolutionLabel = computed(() => {
  const r = videoResolution.value
  if (!r || !r.height) return null
  if (r.height >= 1080) return 'HD 1080p'
  if (r.height >= 720) return 'HD 720p'
  if (r.height >= 480) return 'SD 480p'
  return `${r.height}p`
})

async function loadSession() {
  loading.value = true
  error.value = null
  try {
    session.value = await liveSessionsApi.get(sessionId.value)
    joinInfo.value = await liveSessionsApi.getJoinInfo(sessionId.value)
    // Phase 9c — recorded session bo'lsa caption mavjudligini tekshiramiz
    if (session.value.recording_url) {
      checkHasCaptions().catch(() => null)
    }
    if (canManage.value && session.value.status !== 'cancelled') {
      try {
        attendance.value = await liveSessionsApi.listAttendance(sessionId.value)
      } catch {
        attendance.value = []
      }
      try {
        summary.value = await liveSessionsApi.getAttendanceSummary(sessionId.value)
      } catch {
        summary.value = null
      }
    }
    if (session.value.status === 'live') startElapsedTimer()
    // Waiting room — talaba tasdiq kutmoqda bo'lsa poll boshlaymiz
    if (admissionPending.value) startAdmissionPoll()
    // Host: tasdiq talab qiluvchi jonli sessiyada so'rovlarni kuzatamiz
    if (
      canManage.value &&
      session.value.status === 'live' &&
      session.value.requires_approval
    ) {
      startHostAdmissionPoll()
    }
  } catch (e) {
    if (isNotFound(e)) {
      router.replace({ name: 'live-host' })
      return
    }
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

function startElapsedTimer() {
  if (elapsedTimer) clearInterval(elapsedTimer)
  if (!session.value) return
  const startStr = session.value.actual_start ?? session.value.scheduled_start
  const baseMs = new Date(startStr).getTime()
  const tick = () => {
    elapsedSeconds.value = Math.max(0, Math.floor((Date.now() - baseMs) / 1000))
  }
  tick()
  elapsedTimer = setInterval(tick, 1000)
}

onMounted(loadSession)
watch(sessionId, loadSession)

watch(
  [() => session.value?.status, canManage],
  ([status, manage]) => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (status === 'live' && manage) {
      pollTimer = setInterval(async () => {
        try {
          attendance.value = await liveSessionsApi.listAttendance(sessionId.value)
        } catch (e) {
          // Sessiya o'chirilgan (404) bo'lsa pollni to'xtatamiz (memory leak oldini olish)
          if (isNotFound(e) && pollTimer) {
            clearInterval(pollTimer)
            pollTimer = null
          }
        }
      }, 15000)
    }
  },
  { immediate: true },
)

// Qurilma ulansa/uzilsa (USB mikrofon/kamera) ro'yxatni yangilaymiz (hot-plug)
function onDeviceChange() {
  loadDevices().catch(() => null)
}
onMounted(() => {
  navigator.mediaDevices?.addEventListener?.('devicechange', onDeviceChange)
})

onUnmounted(async () => {
  navigator.mediaDevices?.removeEventListener?.('devicechange', onDeviceChange)
  if (pollTimer) clearInterval(pollTimer)
  if (elapsedTimer) clearInterval(elapsedTimer)
  if (qualityPollTimer) clearInterval(qualityPollTimer)
  if (captionsFlushTimer) clearInterval(captionsFlushTimer)
  if (studentCaptionsTimer) clearInterval(studentCaptionsTimer)
  if (admissionPollTimer) clearInterval(admissionPollTimer)
  if (hostAdmissionTimer) clearInterval(hostAdmissionTimer)
  stopServerRecTimer()
  if (joinedRoom.value && !canManage.value) {
    try {
      await liveSessionsApi.leave(sessionId.value)
    } catch {
      // ignore
    }
  }
})

async function startSession() {
  transitioning.value = true
  try {
    session.value = await liveSessionsApi.start(sessionId.value)
    startElapsedTimer()
  } catch (e) {
    error.value = extractErrorMessage(e, t('live.error_start'))
  } finally {
    transitioning.value = false
  }
}

async function endSession() {
  const ok = await confirm({
    title: t('live.confirm_end'),
    variant: 'danger',
    confirmLabel: t('common.confirm'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  // Attendance poll'ni darrov to'xtatamiz — eskirgan ma'lumot/race oldini olish
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  transitioning.value = true
  try {
    // Agar recording faol bo'lsa, avval to'xtatib MinIO'ga yuklash
    if (recorder.isRecording.value) {
      showRecordingHint(t('live.recording_hint_uploading'))
      await recorder.stop()
    }
    nativeRoomRef.value?.hangup()
    session.value = await liveSessionsApi.end(sessionId.value)
    attendance.value = await liveSessionsApi.listAttendance(sessionId.value)
    summary.value = await liveSessionsApi.getAttendanceSummary(sessionId.value)
    if (elapsedTimer) clearInterval(elapsedTimer)
  } catch (e) {
    error.value = extractErrorMessage(e, t('live.error_end'))
  } finally {
    transitioning.value = false
  }
}

async function hangup() {
  nativeRoomRef.value?.hangup()
  if (!canManage.value) {
    try {
      await liveSessionsApi.leave(sessionId.value)
    } catch {
      // ignore
    }
  }
  router.back()
}

async function recomputeAttendance() {
  recomputing.value = true
  try {
    summary.value = await liveSessionsApi.recomputeAttendance(sessionId.value)
    attendance.value = await liveSessionsApi.listAttendance(sessionId.value)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    recomputing.value = false
  }
}

function onRecordingUploaded(updated: LiveSession) {
  session.value = updated
}

async function onRecordingDelete() {
  const ok = await confirm({
    title: t('live.recording_confirm_delete'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  try {
    session.value = await liveSessionsApi.deleteRecording(sessionId.value)
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    error.value = msg
    toast.error(msg)
  }
}

// === NativeRoom event handlers ===

async function onRoomConnected() {
  roomConnected.value = true
  joinedRoom.value = true
  // Permission'lar berilgan — endi device label'lar to'liq ko'rinadi
  void loadDevices()
  // Phase 5b.5 — quality bar polling (resolution + RTT, 3 soniyada bir)
  pollQualityStats()
  if (qualityPollTimer) clearInterval(qualityPollTimer)
  qualityPollTimer = setInterval(pollQualityStats, 3000)
  if (!canManage.value) {
    try {
      await liveSessionsApi.join(sessionId.value)
    } catch {
      // ignore
    }
  }
}

async function onRoomDisconnected() {
  roomConnected.value = false
  joinedRoom.value = false
  // Host darsni yakunlagan bo'lsa xona o'chiriladi -> bu yerga tushamiz.
  // Sessiya statusini yangilaymiz: 'ended' bo'lsa avtomatik yakuniy ekran chiqadi.
  try {
    const s = await liveSessionsApi.get(sessionId.value)
    session.value = s
  } catch {
    // ignore — sessiya o'chirilgan bo'lishi mumkin
  }
}

let errorClearTimer: ReturnType<typeof setTimeout> | null = null
function setTransientError(msg: string) {
  error.value = msg
  if (errorClearTimer) clearTimeout(errorClearTimer)
  errorClearTimer = setTimeout(() => {
    error.value = null
  }, 5000)
}
function onRoomError(message: string) {
  // Phase 55.4 — ekran ulashish ruxsati yo'q (host bermagan)
  if (message === 'screen-permission-denied') {
    setTransientError(t('live.screen_not_allowed'))
    return
  }
  // Phase 5b.9 — permission errorni alohida banner sifatida ko'rsatamiz (toast emas)
  if (isPermissionError(message)) {
    permissionDenied.value = true
    return
  }
  // Texnik xom xabarni foydalanuvchiga ko'rsatmaymiz — console'ga, ekranga tushunarli
  console.warn('[LiveKit] room error:', message)
  setTransientError(t('live.error_connection'))
}

// Phase 5b.4 / 7a — Recording: in-browser MediaRecorder + MinIO upload
const recordingHint = ref<string | null>(null)
let recordingHintTimer: ReturnType<typeof setTimeout> | null = null
function showRecordingHint(msg: string) {
  recordingHint.value = msg
  if (recordingHintTimer) clearTimeout(recordingHintTimer)
  recordingHintTimer = setTimeout(() => {
    recordingHint.value = null
  }, 6000)
}

const recorder = useLiveRecorder()

// Yozuv hajmi katta bo'lib ketsa (~700MB) host'ni ogohlantiramiz (OOM oldini olish)
watch(
  () => recorder.sizeWarning.value,
  (warn) => {
    if (warn) showRecordingHint(t('live.recording_size_warning'))
  },
)

// Phase 9c — real-time captions (Web Speech API, host only)
const speech = useSpeechRecognition()
const captionsEnabled = ref(false)
const captionsBuffer = ref<LiveCaptionItem[]>([])
let captionsFlushTimer: ReturnType<typeof setInterval> | null = null
const currentCaption = ref<string>('')
const captionLang = ref<'uz-UZ' | 'ru-RU' | 'en-US'>('ru-RU')  // Web Speech API uz-UZ tilini cheklangan qo'llab-quvvatlaydi

async function flushCaptions(): Promise<void> {
  if (!session.value) return
  if (captionsBuffer.value.length === 0) return
  const items = captionsBuffer.value.splice(0, captionsBuffer.value.length)
  try {
    await liveCaptionsApi.postBatch(session.value.id, items)
  } catch {
    // ignore — keyingi flush'da yana urinib ko'ramiz
    captionsBuffer.value.unshift(...items)
  }
}

function onCaptionSegment(seg: CaptionSegment): void {
  currentCaption.value = seg.text
  if (seg.isFinal) {
    captionsBuffer.value.push({
      start_ms: seg.startMs,
      end_ms: seg.endMs,
      text: seg.text,
      lang: captionLang.value.split('-')[0],
    })
  }
}

function toggleCaptions(): void {
  if (!canManage.value) return
  if (captionsEnabled.value) {
    speech.stop()
    captionsEnabled.value = false
    if (captionsFlushTimer) {
      clearInterval(captionsFlushTimer)
      captionsFlushTimer = null
    }
    flushCaptions().catch(() => null)
    currentCaption.value = ''
  } else {
    if (!speech.supported.value) {
      setTransientError(t('live.captions_unsupported'))
      return
    }
    speech.start(captionLang.value, onCaptionSegment)
    captionsEnabled.value = true
    captionsFlushTimer = setInterval(() => {
      flushCaptions().catch(() => null)
    }, 5000)
  }
}

// Phase 9c — recorded playback uchun caption ro'yxati (faqat exist bo'lsa)
const hasCaptions = ref(false)
const captionsVttUrl = computed(() =>
  session.value ? liveCaptionsApi.vttUrl(session.value.id) : '',
)
async function checkHasCaptions(): Promise<void> {
  if (!session.value) return
  try {
    const items = await liveCaptionsApi.list(session.value.id)
    hasCaptions.value = items.length > 0
  } catch {
    hasCaptions.value = false
  }
}

// Phase 9c — talaba (non-host) uchun: serverdan oxirgi caption'larni pull qilish
let studentCaptionsTimer: ReturnType<typeof setInterval> | null = null
const studentCaptionsEnabled = ref(false)
let lastStudentCaptionId = 0
function toggleStudentCaptions(): void {
  if (canManage.value) return
  if (studentCaptionsEnabled.value) {
    if (studentCaptionsTimer) clearInterval(studentCaptionsTimer)
    studentCaptionsTimer = null
    studentCaptionsEnabled.value = false
    currentCaption.value = ''
    return
  }
  studentCaptionsEnabled.value = true
  studentCaptionsTimer = setInterval(async () => {
    if (!session.value) return
    try {
      const items = await liveCaptionsApi.list(session.value.id)
      if (items.length > 0) {
        const latest = items[items.length - 1]
        if (latest.id > lastStudentCaptionId) {
          lastStudentCaptionId = latest.id
          currentCaption.value = latest.text
          setTimeout(() => {
            if (currentCaption.value === latest.text) currentCaption.value = ''
          }, 5000)
        }
      }
    } catch {
      // ignore
    }
  }, 5000)
}

// Phase 55.5 — klient canvas recorder (toggleRecording) olib tashlandi:
// tab fonida muzlab qora ekran berardi. Endi server egress ishlatiladi.
// `recorder` composable hali REC indikatori va RecordingUploader (zaxira
// qo'lda yuklash) uchun saqlanadi.

// === Server-side recording (egress) — Phase 32 / 55.5 (asosiy yozuv usuli) ===
// Klient canvas recorder tab fonida muzlab qora ekran berardi; egress server
// tomonda yozadi (livekit namespace, media 127.0.0.1:7882) — ishonchli.
const serverRecording = ref(false)
const togglingServerRec = ref(false)
const serverRecElapsed = ref(0)
let serverRecTimer: ReturnType<typeof setInterval> | null = null
function startServerRecTimer() {
  serverRecElapsed.value = 0
  if (serverRecTimer) clearInterval(serverRecTimer)
  serverRecTimer = setInterval(() => {
    serverRecElapsed.value += 1
  }, 1000)
}
function stopServerRecTimer() {
  if (serverRecTimer) clearInterval(serverRecTimer)
  serverRecTimer = null
}
async function toggleServerRecording() {
  togglingServerRec.value = true
  try {
    if (serverRecording.value) {
      await liveSessionsApi.egressStop(sessionId.value)
      serverRecording.value = false
      stopServerRecTimer()
      showRecordingHint(t('live.server_rec_stopped'))
    } else {
      await liveSessionsApi.egressStart(sessionId.value)
      serverRecording.value = true
      startServerRecTimer()
      showRecordingHint(t('live.server_rec_started'))
    }
  } catch (e) {
    setTransientError(extractErrorMessage(e, t('live.server_rec_failed')))
  } finally {
    togglingServerRec.value = false
  }
}

function onAudioMute(muted: boolean) {
  audioMuted.value = muted
}
function onVideoMute(muted: boolean) {
  videoMuted.value = muted
}
function onScreenShare(active: boolean) {
  screenSharing.value = active
}
function onScreenAllowed(allowed: boolean) {
  screenAllowed.value = allowed
}
function onQualityChanged(q: string) {
  const v = String(q).toLowerCase()
  if (v.includes('excellent')) connQuality.value = 'excellent'
  else if (v.includes('good')) connQuality.value = 'good'
  else if (v.includes('poor') || v.includes('lost')) connQuality.value = 'poor'
  else connQuality.value = 'unknown'
}
function onParticipants(list: ParticipantState[]) {
  participants.value = list
  // Attach tracks after DOM update
  void nextTick(() => attachAllTracks())
}
function onChat(msg: ChatMessage) {
  chatLog.value.push(msg)
  nextTick(() => {
    if (chatLogRef.value) {
      chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight
    }
  })
}

function attachAllTracks() {
  if (!nativeRoomRef.value) return
  // Main video — screen share priority
  const main = mainParticipant.value
  if (main && mainVideoRef.value) {
    // Use enum from imported module — LiveKit Track.Source
    const source = main.isScreenSharing ? 'screen_share' : 'camera'
    nativeRoomRef.value.attachTrack(
      mainVideoRef.value,
      main.identity,
      // Source enum: LiveKit "screen_share" yoki "camera"
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      source as any,
    )
  }
  // Thumbnails (camera only)
  for (const p of thumbnailParticipants.value) {
    const el = thumbRefs.value[p.identity]
    if (el) {
      nativeRoomRef.value.attachTrack(el, p.identity)
    }
  }
}

watch(participants, () => {
  void nextTick(() => attachAllTracks())
})

// === Control button handlers ===

function toggleMic() {
  nativeRoomRef.value?.toggleAudio()
}
function toggleCam() {
  nativeRoomRef.value?.toggleVideo()
}
function toggleScreen() {
  nativeRoomRef.value?.toggleScreenShare()
}

// Phase 55.4 — host talabaga ekran ulashish ruxsatini beradi/oladi
const grantedScreen = ref<Set<number>>(new Set())
async function toggleScreenGrant(userId: number) {
  const allow = !grantedScreen.value.has(userId)
  try {
    await liveSessionsApi.setScreenshare(sessionId.value, userId, allow)
    const next = new Set(grantedScreen.value)
    if (allow) next.add(userId)
    else next.delete(userId)
    grantedScreen.value = next
  } catch (e) {
    setTransientError(extractErrorMessage(e, t('live.screen_grant_failed')))
  }
}
function sendChat() {
  const text = chatInput.value.trim()
  if (!text) return
  void nativeRoomRef.value?.sendChat(text)
  chatInput.value = ''
}

function statusVariant(s: LiveStatus): 'default' | 'success' | 'warning' {
  if (s === 'live') return 'success'
  if (s === 'cancelled') return 'warning'
  return 'default'
}

function fmtDateTime(s: string | null): string {
  if (!s) return '—'
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

function fmtChatTime(ts: number): string {
  try {
    return formatDate(ts, locale.value, {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

function fmtSize(bytes: number | null): string {
  if (!bytes) return '—'
  const mb = bytes / (1024 * 1024)
  return mb < 1024 ? `${mb.toFixed(1)} MB` : `${(mb / 1024).toFixed(2)} GB`
}

function fmtDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`
}

function initials(name: string): string {
  return name
    .split(' ')
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
</script>

<template>
  <!-- LIVE SHELL — fullscreen dark mode per wireframe 15-live-class.html -->
  <Teleport
    v-if="session && session.status === 'live' && joinInfo"
    to="body"
  >
    <div class="live-shell">
      <!-- Waiting room — talaba host tasdig'ini kutmoqda -->
      <div v-if="admissionPending" class="admission-wait">
        <div class="admission-card">
          <div class="admission-spin"></div>
          <div class="admission-title">{{ t('live.waiting_title') }}</div>
          <div class="admission-sub">{{ t('live.waiting_hint') }}</div>
          <button class="ctrl-btn danger admission-leave" @click="hangup">
            {{ t('live.ctrl_hangup') }}
          </button>
        </div>
      </div>

      <!-- Host: kutayotgan kirish so'rovlari -->
      <div
        v-if="canManage && pendingAdmissions.length"
        class="admission-host-panel"
      >
        <div class="admission-host-title">
          {{ t('live.admissions_title', { n: pendingAdmissions.length }) }}
        </div>
        <div
          v-for="a in pendingAdmissions"
          :key="a.user_id"
          class="admission-row"
        >
          <span class="admission-name">{{ a.full_name }}</span>
          <div class="admission-actions">
            <button class="admission-btn admit" @click="decideAdmission(a.user_id, true)">
              {{ t('live.admit') }}
            </button>
            <button class="admission-btn deny" @click="decideAdmission(a.user_id, false)">
              {{ t('live.deny') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Native WebRTC component (no UI, just handles connection) -->
      <NativeRoom
        v-if="liveKitUrl && joinInfo.embed_token"
        ref="nativeRoomRef"
        :url="liveKitUrl"
        :token="joinInfo.embed_token"
        :display-name="auth.user?.full_name ?? ''"
        :auto-publish="true"
        :audio-only="audioOnly"
        @connected="onRoomConnected"
        @disconnected="onRoomDisconnected"
        @error="onRoomError"
        @audio-mute="onAudioMute"
        @video-mute="onVideoMute"
        @screen-share="onScreenShare"
        @participants="onParticipants"
        @chat="onChat"
        @quality-changed="onQualityChanged"
        @rtt="onRtt"
        @audio-level="onAudioLevel"
        @reaction="onReaction"
        @hand-raise="onHandRaise"
        @screen-share-allowed="onScreenAllowed"
        @qa="onQa"
      />

      <!-- Hidden audio mixer for main participant (so we hear them) -->
      <audio ref="mainAudioRef" autoplay style="display: none"></audio>

      <!-- HEADER -->
      <div class="live-header">
        <div class="header-left">
          <div class="live-pill">
            <span class="live-dot"></span>
            <span>LIVE · {{ formattedElapsed }}</span>
          </div>
          <!-- Phase 5b.4 / 7a / 55.5 — REC indicator (everyone sees), pulsing dot + timer -->
          <div v-if="serverRecording || recorder.isRecording.value || session.is_recording_enabled" class="rec-indicator" :title="t('live.recording_active')">
            <span class="rec-dot"></span>
            <span>REC · {{ fmtDuration(serverRecording ? serverRecElapsed : recorder.elapsedSec.value) }}</span>
          </div>
          <div v-else-if="recorder.isUploading.value" class="rec-indicator" :title="t('live.recording_hint_uploading')">
            <span>⬆ {{ t('live.recording_hint_uploading') }}</span>
          </div>
          <div class="header-title">
            <div class="header-title-main">{{ session.title }}</div>
            <div class="header-title-sub">
              {{ participantCount }} {{ t('live.room_header_count') }} · LIVEKIT
            </div>
          </div>
        </div>
        <div class="header-actions">
          <!-- Phase 55.5 — Yozib olish: server egress (ishonchli, asosiy usul).
               Klient canvas recorder tab fonida qora ekran berardi -> olib tashlandi. -->
          <button
            v-if="canManage"
            class="header-btn"
            :class="{ recording: serverRecording }"
            :disabled="togglingServerRec"
            :title="t('live.server_rec_hint')"
            @click="toggleServerRecording"
          >
            <span class="rec-dot-sm" :class="{ active: serverRecording }"></span>
            {{ serverRecording ? t('live.recording_stop') : t('live.recording_start') }}
          </button>
          <!-- Phase 9c — Captions toggle (host yozadi, talaba ko'radi) -->
          <button
            v-if="canManage"
            class="header-btn"
            :class="{ recording: captionsEnabled }"
            :title="captionsEnabled ? t('live.captions_off') : t('live.captions_on')"
            @click="toggleCaptions"
          >
            CC
            <select
              v-if="captionsEnabled"
              v-model="captionLang"
              class="ml-1 bg-transparent border border-white/30 rounded px-1 text-[10px]"
              @click.stop
              @change="speech.setLang(captionLang)"
            >
              <option value="uz-UZ">UZ</option>
              <option value="ru-RU">RU</option>
              <option value="en-US">EN</option>
            </select>
          </button>
          <button
            v-else
            class="header-btn"
            :class="{ recording: studentCaptionsEnabled }"
            :title="studentCaptionsEnabled ? t('live.captions_off') : t('live.captions_on')"
            @click="toggleStudentCaptions"
          >
            CC
          </button>
          <button v-if="canManage" class="header-btn" @click="activeTab = 'people'">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M2 12c0-2 2-4 5-4s5 2 5 4M7 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" />
            </svg>
            {{ t('live.room_attendance', { n: attendance.length }) }}
          </button>
          <button
            v-if="canManage"
            class="header-btn danger"
            :disabled="transitioning"
            @click="endSession"
          >
            {{ t('live.btn_end') }}
          </button>
          <button v-else class="header-btn" @click="hangup">
            ← {{ t('common.back') }}
          </button>
        </div>
      </div>

      <!-- BODY -->
      <div class="live-body">
        <!-- VIDEO GRID (1fr): main 3fr + thumbnail row 1fr -->
        <div class="video-grid">
          <!-- Phase 5b.6 — Floating reactions overlay (har biri 4s pastdan tepaga) -->
          <div class="reactions-overlay" aria-hidden="true">
            <div
              v-for="r in floatingReactions"
              :key="r.id"
              class="floating-reaction"
              :style="{ left: `${r.startX}%` }"
            >
              <span class="floating-emoji">{{ r.emoji }}</span>
              <span class="floating-nick">{{ r.nick }}</span>
            </div>
          </div>

          <!-- Hand raised counter (host's view) -->
          <div
            v-if="canManage && handRaisedCount > 0"
            class="hand-raised-counter"
            :title="t('live.hand_raised_count', { n: handRaisedCount })"
          >
            ✋ {{ handRaisedCount }}
          </div>

          <!-- Main video -->
          <div class="main-video">
            <video
              v-if="mainParticipant && !mainParticipant.videoMuted"
              ref="mainVideoRef"
              autoplay
              :muted="mainParticipant.isLocal"
              playsinline
              class="main-video-el"
            ></video>
            <div v-else class="main-video-placeholder">
              <div class="main-avatar">
                {{ mainParticipant ? initials(mainParticipant.name) : '—' }}
              </div>
              <div class="main-placeholder-text">
                {{ mainParticipant?.videoMuted ? t('live.video_off') : t('live.no_participants_yet') }}
              </div>
            </div>

            <!-- Speaker overlay (bottom-left) -->
            <div v-if="mainParticipant" class="speaker-overlay">
              <div class="speaker-avatar">
                {{ initials(mainParticipant.name) }}
              </div>
              <div>
                <div class="speaker-name">{{ mainParticipant.name }}</div>
                <div class="speaker-role">
                  {{
                    mainParticipant.isScreenSharing
                      ? t('live.screen_sharing')
                      : mainParticipant.isHost
                        ? t('live.room_role_host')
                        : t('live.room_role_participant')
                  }}
                </div>
              </div>
            </div>

            <!-- Status overlay (top-right) -->
            <div v-if="mainParticipant" class="status-overlay">
              <span :class="{ off: mainParticipant.isMuted }">
                {{ mainParticipant.isMuted ? '🔇' : '🎤' }}
              </span>
              <span :class="{ off: mainParticipant.videoMuted }">
                {{ mainParticipant.videoMuted ? '📷̸' : '📹' }}
              </span>
            </div>
          </div>

          <!-- Thumbnails row -->
          <div class="thumb-row">
            <div
              v-for="p in thumbnailParticipants"
              :key="p.identity"
              class="thumb"
              :class="{ speaking: p.isSpeaking }"
            >
              <video
                v-if="!p.videoMuted"
                :ref="(el) => (thumbRefs[p.identity] = el as HTMLVideoElement | null)"
                autoplay
                :muted="p.isLocal"
                playsinline
                class="thumb-video"
              ></video>
              <div v-else class="thumb-avatar">{{ initials(p.name) }}</div>

              <div class="thumb-name">{{ p.name }}</div>
              <div v-if="p.isMuted" class="thumb-mute">🔇</div>
              <!-- Phase 5b.6 — Hand raised badge -->
              <div v-if="handRaisedIds.has(p.identity)" class="thumb-hand">✋</div>
            </div>

            <div v-if="extraCount > 0" class="thumb thumb-more">
              <div class="thumb-more-count">+{{ extraCount }}</div>
            </div>

            <!-- Fill empty slots with placeholders -->
            <div
              v-for="n in Math.max(0, 5 - thumbnailParticipants.length - (extraCount > 0 ? 1 : 0))"
              :key="`empty-${n}`"
              class="thumb thumb-empty"
            ></div>
          </div>
        </div>

        <!-- SIDE PANEL — mobile'da drawer sifatida slide-in -->
        <div
          v-if="panelOpen"
          class="side-panel-backdrop"
          aria-hidden="true"
          @click="closePanel"
        ></div>
        <aside class="side-panel" :class="{ open: panelOpen }">
          <div class="panel-tabs">
            <button
              class="panel-tab"
              :class="{ active: activeTab === 'chat' }"
              @click="activeTab = 'chat'"
            >
              💬 {{ t('live.room_tab_chat') }}
              <span v-if="chatLog.length" class="tab-count">({{ chatLog.length }})</span>
            </button>
            <button
              class="panel-tab"
              :class="{ active: activeTab === 'people' }"
              @click="activeTab = 'people'"
            >
              👥 {{ t('live.room_tab_people') }}
            </button>
            <button
              class="panel-tab"
              :class="{ active: activeTab === 'qa' }"
              @click="activeTab = 'qa'"
            >
              📋 {{ t('live.room_tab_qa') }}
              <span v-if="unansweredCount > 0" class="tab-badge">{{ unansweredCount }}</span>
            </button>
          </div>

          <!-- Chat tab -->
          <div
            v-if="activeTab === 'chat'"
            ref="chatLogRef"
            class="panel-content panel-chat"
          >
            <div v-if="chatLog.length === 0" class="empty-state">
              {{ t('live.room_chat_empty') }}
            </div>
            <div v-else>
              <div v-for="(m, i) in chatLog" :key="i" class="chat-msg">
                <div class="chat-meta">
                  <span class="chat-name" :class="{ self: m.isLocal }">{{ m.nick }}</span>
                  <span class="chat-time">{{ fmtChatTime(m.ts) }}</span>
                </div>
                <div class="chat-text">{{ m.message }}</div>
              </div>
            </div>
          </div>

          <!-- People tab -->
          <div v-else-if="activeTab === 'people'" class="panel-content">
            <div class="people-section-title">
              {{ t('live.room_people_in_call', { n: participants.length }) }}
            </div>
            <div
              v-for="p in participants"
              :key="p.identity"
              class="person"
            >
              <div
                class="person-avatar"
                :class="{ self: p.isLocal }"
              >{{ initials(p.name) }}</div>
              <div class="person-info">
                <div class="person-name">
                  {{ p.name }}
                  <span v-if="p.isLocal" class="person-you">{{ t('live.room_you') }}</span>
                </div>
                <div class="person-role">
                  {{ p.isHost ? t('live.room_role_host') : t('live.room_role_participant') }}
                </div>
              </div>
              <div class="person-icons">
                <span v-if="p.isMuted" class="person-icon muted">🔇</span>
                <span v-if="p.videoMuted" class="person-icon muted">📷̸</span>
                <span v-if="p.isScreenSharing" class="person-icon">🖥</span>
              </div>
            </div>

            <div v-if="canManage && attendance.length > 0" class="people-section-title mt-6">
              {{ t('live.room_attendance_section', { n: attendance.length }) }}
            </div>
            <ul v-if="canManage" class="attendance-list">
              <li v-for="a in attendance" :key="a.user_id" class="attendance-row">
                <div class="attendance-name">{{ a.full_name }}</div>
                <div class="attendance-meta">
                  <button
                    v-if="a.user_id !== auth.user?.id"
                    class="screen-grant-btn"
                    :class="{ on: grantedScreen.has(a.user_id) }"
                    :title="grantedScreen.has(a.user_id) ? t('live.screen_revoke') : t('live.screen_grant')"
                    @click="toggleScreenGrant(a.user_id)"
                  >
                    <svg width="13" height="13" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="2" y="3" width="14" height="9" rx="1" />
                      <path d="M9 12v3M5 15h8" />
                    </svg>
                  </button>
                  <span class="attendance-min">{{ a.live_minutes }} min</span>
                  <span class="attendance-counted" :class="{ ok: a.is_counted }">
                    {{ a.is_counted ? '✓' : '–' }}
                  </span>
                </div>
              </li>
            </ul>
          </div>

          <!-- Q&A (Phase 55.6) -->
          <div v-else-if="activeTab === 'qa'" class="panel-content qa-panel">
            <ul v-if="sortedQuestions.length" class="qa-list">
              <li v-for="q in sortedQuestions" :key="q.id" class="qa-item" :class="{ answered: q.answered }">
                <button
                  class="qa-vote"
                  :class="{ voted: q.voters.has(myIdentity) }"
                  :disabled="q.from === myIdentity"
                  :title="t('live.qa_upvote')"
                  @click="upvoteQuestion(q.id)"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M6 2.5l4 5H2z" />
                  </svg>
                  <span>{{ q.votes }}</span>
                </button>
                <div class="qa-body">
                  <div class="qa-text">{{ q.text }}</div>
                  <div class="qa-meta">
                    <span class="qa-author">{{ q.nick }}</span>
                    <span v-if="q.answered" class="qa-answered-tag">✓ {{ t('live.qa_answered') }}</span>
                    <button
                      v-else-if="canManage"
                      class="qa-mark"
                      @click="answerQuestion(q.id)"
                    >
                      {{ t('live.qa_mark_answered') }}
                    </button>
                  </div>
                </div>
              </li>
            </ul>
            <div v-else class="empty-state">{{ t('live.qa_empty') }}</div>
          </div>

          <!-- Chat input -->
          <div v-if="activeTab === 'chat'" class="chat-input-wrap">
            <input
              v-model="chatInput"
              class="chat-input"
              :placeholder="t('live.room_chat_placeholder')"
              @keydown.enter="sendChat"
            />
            <button class="chat-send" :disabled="!chatInput.trim()" @click="sendChat">
              →
            </button>
          </div>

          <!-- Q&A input (Phase 55.6) -->
          <div v-if="activeTab === 'qa'" class="chat-input-wrap">
            <input
              v-model="qaInput"
              class="chat-input"
              :placeholder="t('live.qa_placeholder')"
              @keydown.enter="askQuestion"
            />
            <button class="chat-send" :disabled="!qaInput.trim()" @click="askQuestion">
              →
            </button>
          </div>
        </aside>
      </div>

      <!-- Phase 5b.4 — Recording hint (REC toggle bosilganda 6s avto-yopiladi) -->
      <div v-if="recordingHint" class="recording-hint" @click="recordingHint = null">
        <span class="recording-hint-icon">●</span>
        <span class="recording-hint-msg">{{ recordingHint }}</span>
        <button class="recording-hint-close" type="button" aria-label="×">×</button>
      </div>

      <!-- Live error toast (mic/cam permission etc.) — auto-dismiss 5s -->
      <div v-if="error" class="live-error-toast" @click="error = null">
        <span class="live-error-icon">⚠</span>
        <span class="live-error-msg">{{ error }}</span>
        <button class="live-error-close" type="button" :aria-label="t('common.close')">×</button>
      </div>

      <!-- Phase 5b.9 — Permission denied banner (manual dismiss) -->
      <div v-if="permissionDenied" class="permission-banner">
        <div class="permission-icon">⚠</div>
        <div class="permission-body">
          <div class="permission-title">{{ t('live.permission_denied_title') }}</div>
          <div class="permission-help">{{ t('live.permission_denied_help') }}</div>
          <div class="permission-actions">
            <button
              type="button"
              class="permission-btn primary"
              :disabled="retryingPermission"
              @click="retryPermissions(true)"
            >
              {{ retryingPermission ? t('common.loading') : t('live.permission_retry') }}
            </button>
            <button
              type="button"
              class="permission-btn"
              :disabled="retryingPermission"
              @click="retryPermissions(false)"
            >
              🎙 {{ t('live.permission_audio_only') }}
            </button>
            <button
              type="button"
              class="permission-btn ghost"
              @click="dismissPermissionBanner"
            >
              {{ t('live.permission_listen_only') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Phase 9c — Caption overlay (host yoki student CC yoqsa) -->
      <div
        v-if="(captionsEnabled || studentCaptionsEnabled) && currentCaption"
        class="caption-overlay"
      >
        {{ currentCaption }}
      </div>

      <!-- BOTTOM CONTROLS -->
      <div class="live-controls">
        <!-- Mic + level meter (Phase 5b.3) -->
        <div class="ctrl-mic-group">
          <button
            class="ctrl-btn"
            :class="{ off: audioMuted, on: !audioMuted }"
            :title="t('live.ctrl_mic')"
            @click="toggleMic"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="2" width="6" height="10" rx="3" />
              <path d="M3 8a6 6 0 0 0 12 0M9 14v2" />
              <path v-if="audioMuted" d="M2 2l14 14" />
            </svg>
          </button>
          <div v-if="!audioMuted" class="audio-level" :title="t('live.audio_level')">
            <span
              v-for="(active, i) in audioLevelBars"
              :key="i"
              class="audio-level-bar"
              :class="{ active }"
              :style="{ height: `${4 + i * 3}px` }"
            ></span>
          </div>
        </div>
        <button
          class="ctrl-btn"
          :class="{ off: videoMuted, on: !videoMuted }"
          :title="t('live.ctrl_cam')"
          @click="toggleCam"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="5" width="11" height="9" rx="1" />
            <path d="M13 8l3-2v7l-3-2" />
            <path v-if="videoMuted" d="M2 2l14 14" />
          </svg>
        </button>
        <!-- Phase 5b.6 — Reactions picker -->
        <Menu as="div" class="relative">
          <MenuButton class="ctrl-btn" :title="t('live.ctrl_reaction')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="9" />
              <circle cx="9" cy="10" r="0.7" fill="currentColor" />
              <circle cx="15" cy="10" r="0.7" fill="currentColor" />
              <path d="M8 14c1 1.5 2.5 2.5 4 2.5s3-1 4-2.5" />
            </svg>
          </MenuButton>
          <transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
          >
            <MenuItems
              class="absolute right-0 bottom-full mb-2 rounded-full border border-[#27272a] bg-[#18181b] shadow-lg z-50 focus:outline-none px-2 py-1.5 flex gap-1"
            >
              <MenuItem
                v-for="e in REACTION_EMOJIS"
                :key="e"
                v-slot="{ active }"
                as="template"
              >
                <button
                  type="button"
                  :class="[
                    'reaction-pick-btn',
                    active ? 'reaction-pick-active' : '',
                  ]"
                  @click="sendReaction(e)"
                >{{ e }}</button>
              </MenuItem>
            </MenuItems>
          </transition>
        </Menu>

        <!-- Phase 5b.6 — Hand raise -->
        <button
          class="ctrl-btn"
          :class="{ 'hand-raised': myHandRaised }"
          :title="t(myHandRaised ? 'live.ctrl_hand_lower' : 'live.ctrl_hand_raise')"
          @click="toggleHandRaise"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 14V5a1.5 1.5 0 1 1 3 0v6" />
            <path d="M12 11V3.5a1.5 1.5 0 1 1 3 0V11" />
            <path d="M15 11V5.5a1.5 1.5 0 1 1 3 0V14" />
            <path d="M9 14H7a2 2 0 0 0-2 2v2c0 3 2 5 5 5h4c3 0 5-2 5-5v-4" />
          </svg>
        </button>

        <div class="ctrl-sep"></div>
        <button
          class="ctrl-btn"
          :class="{ active: screenSharing }"
          :disabled="!isHost && !screenAllowed"
          :title="!isHost && !screenAllowed ? t('live.screen_not_allowed') : t('live.ctrl_screen')"
          @click="toggleScreen"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="14" height="9" rx="1" />
            <path d="M9 12v3M5 15h8" />
            <path v-if="!isHost && !screenAllowed" d="M2 2l14 14" />
          </svg>
        </button>
        <div class="ctrl-sep"></div>

        <!-- Phase 5b.2 — Device selector dropdown -->
        <Menu as="div" class="relative">
          <MenuButton class="ctrl-btn" :title="t('live.ctrl_devices')">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="9" r="2.5" />
              <path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.5 3.5l1.5 1.5M13 13l1.5 1.5M3.5 14.5l1.5-1.5M13 5l1.5-1.5" />
            </svg>
          </MenuButton>
          <transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
          >
            <MenuItems
              class="absolute right-0 bottom-full mb-2 w-72 rounded-md border border-[#27272a] bg-[#18181b] shadow-lg z-50 focus:outline-none overflow-hidden text-white"
            >
              <div class="px-4 py-2.5 border-b border-[#27272a]">
                <span class="font-mono text-[10px] uppercase tracking-widest text-white/60">
                  {{ t('live.ctrl_devices') }}
                </span>
              </div>

              <!-- Mic group -->
              <div class="px-3 py-2 border-b border-[#27272a]">
                <div class="font-mono text-[10px] uppercase tracking-wider text-white/50 mb-1.5 px-1">
                  {{ t('live.lobby_device_mic') }}
                </div>
                <div v-if="audioInputs.length === 0" class="text-[12px] text-white/40 px-1 py-1">
                  {{ t('live.lobby_device_none') }}
                </div>
                <MenuItem
                  v-for="d in audioInputs"
                  :key="`mic-${d.value}`"
                  v-slot="{ active }"
                  as="template"
                >
                  <button
                    type="button"
                    :class="[
                      'w-full flex items-center gap-2 px-2 py-1.5 rounded text-[12.5px] text-left transition-colors',
                      active ? 'bg-white/10' : '',
                      currentMicId === d.value ? 'text-white font-medium' : 'text-white/70',
                    ]"
                    @click="switchMic(d.value)"
                  >
                    <span class="flex-1 truncate">{{ d.label }}</span>
                    <svg
                      v-if="currentMicId === d.value"
                      width="12" height="12" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" stroke-width="2.5"
                    >
                      <path d="m5 12 5 5L20 7" />
                    </svg>
                  </button>
                </MenuItem>
              </div>

              <!-- Cam group -->
              <div class="px-3 py-2 border-b border-[#27272a]">
                <div class="font-mono text-[10px] uppercase tracking-wider text-white/50 mb-1.5 px-1">
                  {{ t('live.lobby_device_cam') }}
                </div>
                <div v-if="videoInputs.length === 0" class="text-[12px] text-white/40 px-1 py-1">
                  {{ t('live.lobby_device_none') }}
                </div>
                <MenuItem
                  v-for="d in videoInputs"
                  :key="`cam-${d.value}`"
                  v-slot="{ active }"
                  as="template"
                >
                  <button
                    type="button"
                    :class="[
                      'w-full flex items-center gap-2 px-2 py-1.5 rounded text-[12.5px] text-left transition-colors',
                      active ? 'bg-white/10' : '',
                      currentCamId === d.value ? 'text-white font-medium' : 'text-white/70',
                    ]"
                    @click="switchCam(d.value)"
                  >
                    <span class="flex-1 truncate">{{ d.label }}</span>
                    <svg
                      v-if="currentCamId === d.value"
                      width="12" height="12" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" stroke-width="2.5"
                    >
                      <path d="m5 12 5 5L20 7" />
                    </svg>
                  </button>
                </MenuItem>
              </div>

              <!-- Speaker group -->
              <div class="px-3 py-2">
                <div class="font-mono text-[10px] uppercase tracking-wider text-white/50 mb-1.5 px-1">
                  {{ t('live.lobby_device_speaker') }}
                </div>
                <div v-if="audioOutputs.length === 0" class="text-[12px] text-white/40 px-1 py-1">
                  {{ t('live.lobby_device_none') }}
                </div>
                <MenuItem
                  v-for="d in audioOutputs"
                  :key="`spk-${d.value}`"
                  v-slot="{ active }"
                  as="template"
                >
                  <button
                    type="button"
                    :class="[
                      'w-full flex items-center gap-2 px-2 py-1.5 rounded text-[12.5px] text-left transition-colors',
                      active ? 'bg-white/10' : '',
                      currentSpeakerId === d.value ? 'text-white font-medium' : 'text-white/70',
                    ]"
                    @click="switchSpeaker(d.value)"
                  >
                    <span class="flex-1 truncate">{{ d.label }}</span>
                    <svg
                      v-if="currentSpeakerId === d.value"
                      width="12" height="12" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" stroke-width="2.5"
                    >
                      <path d="m5 12 5 5L20 7" />
                    </svg>
                  </button>
                </MenuItem>
              </div>

              <!-- Phase 5b.7 — Video effects (background blur) -->
              <div class="px-3 py-2 border-t border-[#27272a]">
                <div class="font-mono text-[10px] uppercase tracking-wider text-white/50 mb-1.5 px-1">
                  {{ t('live.video_effects') }}
                </div>
                <button
                  type="button"
                  :class="[
                    'w-full flex items-center gap-2 px-2 py-1.5 rounded text-[12.5px] text-left transition-colors',
                    backgroundBlurEnabled ? 'text-white font-medium' : 'text-white/70',
                  ]"
                  :disabled="backgroundBlurLoading"
                  @click="toggleBackgroundBlur"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="9" stroke-dasharray="3 2" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span class="flex-1">{{ t('live.bg_blur') }}</span>
                  <span v-if="backgroundBlurLoading" class="text-[10px] text-white/40">...</span>
                  <svg
                    v-else-if="backgroundBlurEnabled"
                    width="12" height="12" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="2.5"
                  >
                    <path d="m5 12 5 5L20 7" />
                  </svg>
                </button>
              </div>
            </MenuItems>
          </transition>
        </Menu>

        <!-- Phase 5b.8 — Mobile: panel toggle (chat/people) -->
        <button
          class="ctrl-btn ctrl-mobile-panel"
          :class="{ active: panelOpen }"
          :title="t('live.ctrl_panel_toggle')"
          @click="togglePanel"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="2" y="3" width="14" height="12" rx="1.5" />
            <path d="M5 6h8M5 9h6M5 12h4" />
          </svg>
        </button>

        <div class="ctrl-sep"></div>
        <button class="ctrl-btn danger" :title="t('live.ctrl_hangup')" @click="hangup">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
            <path d="M9 12c-3 0-5-1-7-3 0-1 0-2 1-3 3-2 9-2 12 0 1 1 1 2 1 3-2 2-4 3-7 3z" />
          </svg>
        </button>

        <!-- Phase 5b.5 — Network quality bar -->
        <div class="ctrl-info">
          <div v-if="!roomConnected" class="quality-bar">
            <span class="conn-status">● {{ t('live.connecting') }}</span>
          </div>
          <div v-else class="quality-bar" :title="qualityLabel">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M1 6c4-3 8-3 12 0M3 9c3-2 5-2 8 0M5 12c1-1 3-1 4 0" />
            </svg>
            <div class="signal-bars" :class="qualityClass">
              <span v-for="i in 4" :key="i" :class="{ active: i <= signalBars }"></span>
            </div>
            <span v-if="resolutionLabel" class="quality-meta">{{ resolutionLabel }}</span>
            <span class="quality-meta" :class="qualityClass">{{ qualityLabel }}</span>
            <span v-if="connRtt !== null" class="quality-meta">{{ connRtt }}{{ t('live.rtt_ms') }}</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Non-live states (AppLayout-aware) -->
  <template v-if="!(session && session.status === 'live' && joinInfo)">
    <div v-if="loading && !session" class="text-center py-12 text-muted-foreground">
      {{ t('common.loading') }}
    </div>
    <UiAlert v-else-if="error && !session" variant="danger">{{ error }}</UiAlert>

    <template v-else-if="session">
      <div class="mb-6">
        <button
          type="button"
          class="text-[12px] font-mono text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1"
          @click="router.back()"
        >
          ← {{ t('common.back') }}
        </button>
        <div class="flex items-end justify-between gap-6">
          <div class="min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <UiBadge :variant="statusVariant(session.status)" with-dot>
                {{ t(`live.status_${session.status}`) }}
              </UiBadge>
              <UiBadge variant="default">{{ t('live.native_provider') }}</UiBadge>
            </div>
            <h1 class="page-title mb-1.5 truncate">{{ session.title }}</h1>
            <p class="page-subtitle">
              {{ fmtDateTime(session.scheduled_start) }} · {{ session.duration_minutes }} min
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <UiButton
              v-if="canManage && session.status === 'scheduled'"
              :loading="transitioning"
              @click="startSession"
            >
              {{ t('live.btn_start') }}
            </UiButton>
          </div>
        </div>
      </div>

      <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

      <UiCard v-if="session.status === 'scheduled'" class="mb-4">
        <p class="text-[13px] text-muted-foreground">
          <template v-if="canManage">{{ t('live.hint_host_not_started') }}</template>
          <template v-else>{{ t('live.hint_student_not_started') }}</template>
        </p>
      </UiCard>

      <UiCard v-if="session.status === 'cancelled'" class="mb-4">
        <p class="text-[13px] text-warning-700 dark:text-warning-300">
          {{ t('live.hint_cancelled') }}
        </p>
      </UiCard>

      <!-- ENDED: summary + recording -->
      <template v-if="session.status === 'ended'">
        <UiCard
          v-if="!session.recording_url && !canManage"
          class="mb-4"
        >
          <p class="text-[13px] text-muted-foreground">
            {{ t('live.hint_ended_no_recording') }}
          </p>
        </UiCard>

        <UiCard v-if="canManage && summary" class="mb-4">
          <template #header>
            <div>
              <div class="mono-tag mb-1">{{ t('live.summary_tag') }}</div>
              <h3 class="text-base font-semibold">{{ t('live.summary_title') }}</h3>
            </div>
            <UiButton
              variant="ghost"
              size="sm"
              :loading="recomputing"
              @click="recomputeAttendance"
            >
              {{ t('live.summary_recompute') }}
            </UiButton>
          </template>

          <dl class="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-3 text-[13px]">
            <div>
              <dt class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {{ t('live.summary_total') }}
              </dt>
              <dd class="font-medium mt-1">{{ summary.total_participants }}</dd>
            </div>
            <div>
              <dt class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {{ t('live.summary_joined') }}
              </dt>
              <dd class="font-medium mt-1">{{ summary.joined_participants }}</dd>
            </div>
            <div>
              <dt class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {{ t('live.summary_counted') }}
              </dt>
              <dd class="font-medium mt-1">
                {{ summary.counted_participants }}
                <span class="font-mono text-[11px] text-muted-foreground">
                  · {{ summary.counted_percent }}%
                </span>
              </dd>
            </div>
            <div>
              <dt class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {{ t('live.summary_avg_minutes') }}
              </dt>
              <dd class="font-medium mt-1 font-mono">
                {{ summary.average_minutes }} / {{ summary.duration_minutes }} min
              </dd>
            </div>
          </dl>
        </UiCard>

        <UiCard v-if="session.recording_url" no-padding class="mb-4">
          <video
            :src="session.recording_url"
            :poster="session.thumbnail_url ?? undefined"
            controls
            preload="metadata"
            crossorigin="anonymous"
            class="w-full max-h-[70vh] bg-foreground"
          >
            <track
              v-if="hasCaptions"
              :src="captionsVttUrl"
              kind="captions"
              srclang="uz"
              :label="t('live.captions_track_label')"
              default
            />
          </video>
          <div class="px-4 py-3 border-t border-border flex items-center justify-between gap-3 text-[12px]">
            <div class="flex items-center gap-3 font-mono text-muted-foreground">
              <span>{{ t('live.recording_size', { size: fmtSize(session.recording_size_bytes) }) }}</span>
              <span v-if="session.recording_duration_seconds">
                · {{ t('live.recording_duration', { dur: fmtDuration(session.recording_duration_seconds) }) }}
              </span>
            </div>
            <div v-if="canManage" class="flex items-center gap-2">
              <a
                :href="session.recording_url"
                download
                class="inline-flex items-center justify-center rounded-md border border-transparent bg-transparent text-foreground hover:bg-muted px-2.5 py-1.5 text-xs font-medium transition-colors"
              >
                {{ t('live.recording_download') }}
              </a>
              <UiButton
                variant="ghost"
                size="sm"
                class="text-danger-600"
                @click="onRecordingDelete"
              >
                {{ t('common.delete') }}
              </UiButton>
            </div>
          </div>
        </UiCard>

        <UiCard v-else-if="canManage" :title="t('live.recording_upload_title')">
          <RecordingUploader :session-id="session.id" @uploaded="onRecordingUploaded" />
        </UiCard>
      </template>
    </template>
  </template>
</template>

<style scoped>
/* ============================================================================
   WAITING ROOM (admission) — Phase 31
   ============================================================================ */
.admission-wait {
  position: absolute;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  background: rgba(9, 9, 11, 0.92);
  backdrop-filter: blur(4px);
}
.admission-card {
  text-align: center;
  color: #e4e4e7;
  max-width: 340px;
  padding: 32px 28px;
}
.admission-spin {
  width: 40px;
  height: 40px;
  margin: 0 auto 18px;
  border: 3px solid rgba(255, 255, 255, 0.15);
  border-top-color: #d2ad5c;
  border-radius: 50%;
  animation: admission-spin 0.9s linear infinite;
}
@keyframes admission-spin {
  to { transform: rotate(360deg); }
}
.admission-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.admission-sub { font-size: 13px; color: #a1a1aa; line-height: 1.5; margin-bottom: 22px; }
.admission-leave { margin: 0 auto; }

.admission-host-panel {
  position: absolute;
  top: 64px;
  right: 16px;
  z-index: 70;
  width: 280px;
  background: #18181b;
  border: 1px solid #3f3f46;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}
.admission-host-title {
  font-size: 12px;
  font-weight: 600;
  color: #d2ad5c;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}
.admission-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid #27272a;
}
.admission-name { font-size: 13px; color: #e4e4e7; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admission-actions { display: flex; gap: 6px; flex-shrink: 0; }
.admission-btn {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
}
.admission-btn.admit { background: #15803d; color: #fff; }
.admission-btn.admit:hover { background: #166534; }
.admission-btn.deny { background: #3f3f46; color: #e4e4e7; }
.admission-btn.deny:hover { background: #52525b; }

/* ============================================================================
   LIVE SHELL — wireframe 15-live-class.html dan to'liq ko'chirilgan
   ============================================================================ */
.live-shell {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: #18181b;
  color: white;
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
  font-family: inherit;
}

/* HEADER */
.live-header {
  padding: 12px 24px;
  background: #18181b;
  border-bottom: 1px solid #27272a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #dc2626;
  color: white;
  border-radius: 4px;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  font-weight: 600;
}
.live-dot {
  width: 8px;
  height: 8px;
  background: white;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(0.85); }
}
/* Phase 5b.4 — REC indicator (qizil pulsing dot + timer) */
/* Phase 9c — caption overlay (live darsda real-time subtitle) */
.caption-overlay {
  position: fixed;
  left: 50%;
  bottom: 110px;
  transform: translateX(-50%);
  max-width: min(900px, 80%);
  padding: 12px 24px;
  background: rgba(0, 0, 0, 0.78);
  color: #fff;
  font-size: 18px;
  line-height: 1.4;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
  z-index: 40;
  pointer-events: none;
}

.rec-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #7f1d1d;
  border: 1px solid #b91c1c;
  border-radius: 12px;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  font-weight: 600;
  color: #fef2f2;
}
.rec-dot {
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}
.rec-dot-sm {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transition: background-color 200ms;
}
.rec-dot-sm.active {
  background: #ef4444;
  animation: pulse 1.5s ease-in-out infinite;
}
.header-btn.recording {
  background: #7f1d1d;
  border-color: #b91c1c;
  color: #fef2f2;
}
.header-btn.recording:hover:not(:disabled) {
  background: #991b1b;
}

.header-title { min-width: 0; }
.header-title-main {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.2;
}
.header-title-sub {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  color: #a1a1aa;
  margin-top: 2px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
.header-btn {
  background: transparent;
  color: white;
  border: 1px solid #27272a;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
}
.header-btn:hover { background: #27272a; }
.header-btn.danger {
  background: #dc2626;
  border-color: #dc2626;
}
.header-btn.danger:hover { background: #b91c1c; }
.header-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* BODY */
.live-body {
  display: grid;
  grid-template-columns: 1fr 320px;
  min-height: 0;
}

/* VIDEO GRID */
.video-grid {
  padding: 16px;
  display: grid;
  gap: 12px;
  grid-template-rows: 3fr 1fr;
  min-height: 0;
  position: relative;  /* reactions overlay anchor */
}

/* Phase 5b.6 — Reactions overlay (pastdan tepaga uchuvchi emoji) */
.reactions-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 5;
}
.floating-reaction {
  position: absolute;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  animation: float-up 4s ease-out forwards;
}
.floating-emoji {
  font-size: 36px;
  line-height: 1;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.5));
}
.floating-nick {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 10px;
  color: white;
  background: rgba(0, 0, 0, 0.6);
  padding: 2px 6px;
  border-radius: 8px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
@keyframes float-up {
  0% { transform: translateY(0) scale(0.5); opacity: 0; }
  10% { transform: translateY(-30px) scale(1); opacity: 1; }
  80% { transform: translateY(-300px) scale(1.2); opacity: 1; }
  100% { transform: translateY(-380px) scale(1.4); opacity: 0; }
}

/* Hand raised counter (host's view, top-right of video grid) */
.hand-raised-counter {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #facc15;
  color: #422006;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 16px;
  z-index: 6;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* Phase 5b.6 — Reaction picker button styling */
.reaction-pick-btn {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  font-size: 20px;
  border-radius: 50%;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 100ms, transform 100ms;
}
.reaction-pick-btn:hover,
.reaction-pick-active {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.15);
}

/* Hand badge on thumbnail */
.thumb-hand {
  position: absolute;
  top: 6px;
  left: 6px;
  background: #facc15;
  color: #422006;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
  z-index: 2;
}

/* Hand raise button active state (yellow, distinct from screen-share's blue) */
.ctrl-btn.hand-raised {
  background: #facc15;
  color: #422006;
}

/* MAIN VIDEO */
.main-video {
  background: #27272a;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
}
.main-video-el {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #0a0a0a;
}
.main-video-placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #52525b;
}
.main-avatar {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: #3f3f46;
  color: #d4d4d8;
  display: grid;
  place-items: center;
  font-size: 36px;
  font-weight: 600;
  margin-bottom: 16px;
}
.main-placeholder-text {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  text-align: center;
}
.speaker-overlay {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(0, 0, 0, 0.6);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(4px);
}
.speaker-avatar {
  width: 32px;
  height: 32px;
  background: #2563eb;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 600;
  color: white;
}
.speaker-name { font-weight: 500; font-size: 13px; color: white; }
.speaker-role { font-size: 10px; color: #a1a1aa; margin-top: 1px; }
.status-overlay {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.6);
  padding: 4px 10px;
  border-radius: 4px;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 12px;
  color: white;
  display: flex;
  gap: 8px;
  backdrop-filter: blur(4px);
}
.status-overlay span.off { opacity: 0.5; }

/* THUMBNAILS */
.thumb-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  min-height: 0;
}
.thumb {
  background: #27272a;
  aspect-ratio: 16/9;
  border-radius: 6px;
  position: relative;
  overflow: hidden;
  display: grid;
  place-items: center;
  color: #71717a;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  border: 2px solid transparent;
  transition: border-color 0.15s;
}
.thumb.speaking { border-color: #4ade80; }
.thumb-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #3f3f46;
  color: #d4d4d8;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 600;
}
.thumb-name {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 2px 6px;
  font-size: 10px;
  border-radius: 3px;
  max-width: calc(100% - 8px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.thumb-mute {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: #dc2626;
  color: white;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 9px;
}
.thumb-more {
  background: #3f3f46;
  border: 1px dashed #52525b;
}
.thumb-more-count {
  font-size: 18px;
  color: #d4d4d8;
  font-weight: 600;
}
.thumb-empty {
  background: #1f1f23;
  border: 1px dashed #27272a;
}

/* SIDE PANEL */
.side-panel {
  background: #18181b;
  border-left: 1px solid #27272a;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-tabs {
  display: flex;
  padding: 12px 16px;
  gap: 4px;
  border-bottom: 1px solid #27272a;
  flex-shrink: 0;
}
.panel-tab {
  padding: 6px 10px;
  font-size: 12px;
  color: #a1a1aa;
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 4px;
  font-family: inherit;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.panel-tab:hover { color: white; }
.panel-tab.active { background: #27272a; color: white; }
.tab-count {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 10px;
}
.tab-badge {
  display: inline-grid;
  place-items: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 700;
  font-family: 'Geist Mono', ui-monospace, monospace;
}

/* Phase 55.6 — Q&A */
.qa-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.qa-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  border: 1px solid #27272a;
  border-radius: 8px;
  background: #18181b;
}
.qa-item.answered { opacity: 0.55; }
.qa-vote {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 34px;
  padding: 4px 0;
  border: 1px solid #3f3f46;
  border-radius: 6px;
  background: transparent;
  color: #a1a1aa;
  cursor: pointer;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.15s;
}
.qa-vote:hover:not(:disabled) { color: white; border-color: #52525b; }
.qa-vote:disabled { opacity: 0.5; cursor: default; }
.qa-vote.voted { color: #60a5fa; border-color: #60a5fa; background: rgba(96, 165, 250, 0.12); }
.qa-body { flex: 1; min-width: 0; }
.qa-text { font-size: 13px; color: #e4e4e7; line-height: 1.4; word-break: break-word; }
.qa-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.qa-author { font-size: 11px; color: #71717a; }
.qa-answered-tag { font-size: 11px; color: #4ade80; font-weight: 600; }
.qa-mark {
  font-size: 11px;
  color: #60a5fa;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.qa-mark:hover { text-decoration: underline; }

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.empty-state {
  text-align: center;
  color: #71717a;
  font-size: 12px;
  padding: 40px 12px;
  line-height: 1.5;
}

/* CHAT */
.panel-chat { display: flex; flex-direction: column; }
.chat-msg { margin-bottom: 12px; font-size: 13px; }
.chat-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.chat-name { font-weight: 600; font-size: 12px; color: #a78bfa; }
.chat-name.self { color: #4ade80; }
.chat-time {
  font-size: 10px;
  color: #71717a;
  font-family: 'Geist Mono', ui-monospace, monospace;
}
.chat-text { color: #d4d4d8; line-height: 1.4; word-break: break-word; }
.chat-input-wrap {
  padding: 12px 16px;
  border-top: 1px solid #27272a;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
.chat-input {
  flex: 1;
  padding: 10px 12px;
  background: #27272a;
  border: 1px solid #3f3f46;
  border-radius: 6px;
  color: white;
  font-family: inherit;
  font-size: 13px;
  outline: none;
}
.chat-input:focus { border-color: #52525b; }
.chat-send {
  background: white;
  color: black;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 700;
  font-size: 14px;
  display: grid;
  place-items: center;
}
.chat-send:disabled { opacity: 0.4; cursor: not-allowed; }

/* PEOPLE */
.people-section-title {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #71717a;
  margin-bottom: 10px;
}
.mt-6 { margin-top: 24px; }
.person {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #27272a;
}
.person-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #3f3f46;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  color: #e4e4e7;
  flex-shrink: 0;
}
.person-avatar.self { background: #4ade80; color: #052e16; }
.person-info { min-width: 0; flex: 1; }
.person-name {
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.person-you {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 9px;
  padding: 1px 5px;
  background: #4ade80;
  color: #052e16;
  border-radius: 3px;
  text-transform: uppercase;
}
.person-role {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 10px;
  color: #71717a;
  margin-top: 2px;
}
.person-icons { display: flex; gap: 6px; flex-shrink: 0; font-size: 12px; }
.person-icon.muted { opacity: 0.7; }

.attendance-list { list-style: none; margin: 0; padding: 0; }
.attendance-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #27272a;
  font-size: 12px;
}
.attendance-name { color: #d4d4d8; }
.attendance-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
}
.attendance-min { color: #a1a1aa; }
.attendance-counted { color: #71717a; }
.attendance-counted.ok { color: #4ade80; }
.screen-grant-btn {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid #3f3f46;
  background: transparent;
  color: #71717a;
  cursor: pointer;
  transition: all 0.15s;
}
.screen-grant-btn:hover { color: #e4e4e7; border-color: #52525b; }
.screen-grant-btn.on {
  color: #4ade80;
  border-color: #4ade80;
  background: rgba(74, 222, 128, 0.12);
}

/* Live error toast (mic/cam permission etc.) */
.live-error-toast {
  position: absolute;
  bottom: 88px;
  left: 50%;
  transform: translateX(-50%);
  background: #7f1d1d;
  color: #fef2f2;
  border: 1px solid #b91c1c;
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  z-index: 10001;
  max-width: 80%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  cursor: pointer;
}
.live-error-icon { font-size: 16px; }
.live-error-msg { flex: 1; }
.live-error-close {
  background: transparent;
  border: none;
  color: #fef2f2;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;
}
.live-error-close:hover { color: white; }

/* BOTTOM CONTROLS */
.live-controls {
  padding: 12px 24px;
  background: #0a0a0a;
  border-top: 1px solid #27272a;
  display: flex;
  justify-content: center;
  gap: 12px;
  align-items: center;
  position: relative;
}
/* Mic button + audio level meter group (Phase 5b.3) */
.ctrl-mic-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #18181b;
  border-radius: 24px;
  padding-right: 12px;
}
.ctrl-mic-group .ctrl-btn {
  background: #27272a;
}
.audio-level {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 22px;
  padding: 2px 0;
}
.audio-level-bar {
  width: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.15);
  transition: background-color 50ms linear;
}
.audio-level-bar.active {
  background: #4ade80;
}
.audio-level-bar:nth-child(4).active,
.audio-level-bar:nth-child(5).active {
  background: #facc15;
}

.ctrl-btn {
  width: 44px;
  height: 44px;
  background: #27272a;
  border: none;
  border-radius: 50%;
  color: white;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.15s;
}
.ctrl-btn:hover { background: #3f3f46; }
.ctrl-btn.on { background: white; color: black; }
.ctrl-btn.off { background: #dc2626; color: white; }
.ctrl-btn.active { background: #2563eb; color: white; }
.ctrl-btn.danger { background: #dc2626; }
.ctrl-btn.danger:hover { background: #b91c1c; }
.ctrl-sep { width: 1px; height: 28px; background: #27272a; }
.ctrl-info {
  margin-left: 24px;
  display: flex;
  gap: 12px;
  align-items: center;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  color: #a1a1aa;
}
.conn-status { color: #71717a; }
.conn-status.good { color: #4ade80; }
.conn-status.poor { color: #f59e0b; }

/* Phase 5b.5 — Network quality bar */
.quality-bar {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  color: #a1a1aa;
}
.signal-bars {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 12px;
}
.signal-bars span {
  width: 3px;
  border-radius: 1px;
  background: rgba(255, 255, 255, 0.18);
}
.signal-bars span:nth-child(1) { height: 30%; }
.signal-bars span:nth-child(2) { height: 55%; }
.signal-bars span:nth-child(3) { height: 80%; }
.signal-bars span:nth-child(4) { height: 100%; }
.signal-bars.good span.active { background: #4ade80; }
.signal-bars.poor span.active { background: #f59e0b; }
.signal-bars span.active { background: #71717a; }  /* fallback */
.quality-meta {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px;
  color: #a1a1aa;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.quality-meta.good { color: #4ade80; }
.quality-meta.poor { color: #f59e0b; }

/* Phase 5b.4 — Recording toggle hint banner */
.recording-hint {
  position: absolute;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10003;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #422006;
  border: 1px solid #facc15;
  border-radius: 8px;
  color: #fef3c7;
  font-size: 13px;
  max-width: 540px;
  width: calc(100% - 32px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  cursor: pointer;
}
.recording-hint-icon {
  color: #ef4444;
  font-size: 16px;
  animation: pulse 1.5s ease-in-out infinite;
}
.recording-hint-msg { flex: 1; line-height: 1.4; }
.recording-hint-close {
  background: transparent;
  border: none;
  color: #fde68a;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;
}

/* Phase 5b.9 — Permission denied banner */
.permission-banner {
  position: absolute;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10002;
  display: flex;
  gap: 14px;
  padding: 14px 18px;
  background: #422006;
  border: 1px solid #facc15;
  border-radius: 8px;
  color: #fef3c7;
  max-width: 580px;
  width: calc(100% - 32px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}
.permission-icon {
  font-size: 24px;
  line-height: 1;
  color: #facc15;
}
.permission-body { flex: 1; }
.permission-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}
.permission-help {
  font-size: 12.5px;
  line-height: 1.5;
  color: #fde68a;
  margin-bottom: 10px;
}
.permission-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.permission-btn {
  background: transparent;
  border: 1px solid #facc15;
  color: #fef3c7;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: background 100ms;
}
.permission-btn:hover:not(:disabled) { background: rgba(250, 204, 21, 0.15); }
.permission-btn.primary {
  background: #facc15;
  color: #422006;
  font-weight: 600;
}
.permission-btn.primary:hover:not(:disabled) { background: #fde047; }
.permission-btn.ghost {
  border-color: transparent;
  color: #fde68a;
}
.permission-btn.ghost:hover { color: white; }
.permission-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Mobile panel toggle — desktop'da yashirilgan, mobile'da ko'rinadi */
.ctrl-mobile-panel { display: none; }

.side-panel-backdrop { display: none; }

/* Tablet (1024px gacha) — side panel drawer ko'rinishida */
@media (max-width: 1024px) {
  .live-body { grid-template-columns: 1fr; }
  .thumb-row { grid-template-columns: repeat(4, 1fr); }

  .ctrl-mobile-panel { display: grid; }

  .side-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 360px;
    max-width: 90vw;
    z-index: 50;
    transform: translateX(100%);
    transition: transform 250ms ease-out;
    box-shadow: -8px 0 24px rgba(0, 0, 0, 0.5);
  }
  .side-panel.open {
    transform: translateX(0);
  }
  .side-panel-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 49;
    animation: backdrop-fade 200ms ease-out;
  }
  @keyframes backdrop-fade {
    from { opacity: 0; }
    to { opacity: 1; }
  }
}

/* Mobile (768px gacha) — stacked header + 1-col video + horizontal scroll thumbs + 56px controls */
@media (max-width: 768px) {
  /* Header: stacked layout */
  .live-header {
    flex-wrap: wrap;
    gap: 8px;
    padding: 10px 16px;
  }
  .header-left {
    flex-wrap: wrap;
    gap: 8px;
    width: 100%;
  }
  .header-title-main {
    font-size: 13px;
    width: 100%;
  }
  .header-title-sub {
    font-size: 10px;
  }
  .header-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }
  .header-btn {
    padding: 6px 10px;
    font-size: 11px;
  }
  .header-btn svg { display: none; }

  /* Video grid: stack rows differently */
  .video-grid {
    padding: 8px;
    gap: 8px;
    grid-template-rows: 1fr auto;
  }
  .main-video {
    border-radius: 6px;
  }
  .main-avatar {
    width: 72px;
    height: 72px;
    font-size: 28px;
  }

  /* Thumbs: horizontal scroll, fixed width */
  .thumb-row {
    grid-template-columns: none;
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    gap: 8px;
    padding-bottom: 4px;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
  }
  .thumb-row::-webkit-scrollbar { display: none; }
  .thumb-row .thumb {
    flex: 0 0 130px;
    height: 80px;
    scroll-snap-align: start;
  }
  .thumb-empty { display: none; }

  /* Side panel mobile */
  .side-panel {
    width: 100vw;
    max-width: 100vw;
  }

  /* Controls: bottom bar full-width, touch-friendly 56px */
  .live-controls {
    padding: 10px 16px;
    gap: 8px;
    flex-wrap: wrap;
  }
  .ctrl-btn {
    width: 48px;
    height: 48px;
  }
  .ctrl-mic-group {
    padding-right: 8px;
  }
  .audio-level {
    display: none;  /* mobile'da joy chegarali — mic visible feedback yetadi */
  }
  .ctrl-sep {
    display: none;
  }

  /* Quality bar: kichik mobile'da */
  .ctrl-info {
    width: 100%;
    margin-top: 4px;
    justify-content: center;
  }
  .quality-bar {
    flex-wrap: wrap;
    justify-content: center;
    gap: 6px;
  }
  .quality-meta {
    font-size: 10px;
  }

  /* Floating reactions kichikroq */
  .floating-emoji {
    font-size: 28px;
  }
  @keyframes float-up {
    0% { transform: translateY(0) scale(0.5); opacity: 0; }
    10% { transform: translateY(-20px) scale(1); opacity: 1; }
    80% { transform: translateY(-180px) scale(1.2); opacity: 1; }
    100% { transform: translateY(-220px) scale(1.4); opacity: 0; }
  }

  /* REC indicator pill: kichikroq */
  .rec-indicator {
    font-size: 10px;
    padding: 3px 8px;
  }

  /* Live error toast mobile */
  .live-error-toast {
    bottom: 110px;
    max-width: 90%;
    font-size: 12px;
  }
}

/* Portrait (orientation media query) — extra tweaks */
@media (max-width: 480px) and (orientation: portrait) {
  .header-btn { padding: 5px 8px; font-size: 10px; }
  .ctrl-btn { width: 44px; height: 44px; }
  .video-grid { padding: 4px; gap: 4px; }
  .thumb-row .thumb {
    flex: 0 0 100px;
    height: 64px;
  }
}
</style>
