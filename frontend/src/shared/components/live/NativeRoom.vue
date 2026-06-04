<script setup lang="ts">
/**
 * Native WebRTC room (LiveKit-based) — tashqi xizmatsiz, bizning docker stackimizda.
 *
 * Komponent o'zi UI render qilmaydi — parent track elementlarini render qiladi
 * va `attachTrack` / `detachTrack` orqali LiveKit track'larini ulaydi.
 */
import {
  ConnectionQuality,
  ConnectionState,
  type LocalVideoTrack,
  type Participant,
  type RemoteParticipant,
  Room,
  RoomEvent,
  Track,
} from 'livekit-client'
import { BackgroundBlur } from '@livekit/track-processors'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface Props {
  url: string
  token: string
  displayName?: string
  autoPublish?: boolean
  audioOnly?: boolean  // Phase 5b.9 — listen-only / mic-only mode (camera disabled)
}

const props = withDefaults(defineProps<Props>(), {
  displayName: '',
  autoPublish: true,
  audioOnly: false,
})

export interface ParticipantState {
  identity: string
  name: string
  isLocal: boolean
  isHost: boolean
  isMuted: boolean
  videoMuted: boolean
  isScreenSharing: boolean
  isSpeaking: boolean
  metadata: Record<string, unknown>
}

export interface ChatMessage {
  from: string
  nick: string
  message: string
  ts: number
  isLocal: boolean
}

export interface ReactionEvent {
  from: string
  nick: string
  emoji: string
  ts: number
}

export interface HandRaiseEvent {
  from: string
  nick: string
  up: boolean
}

const emit = defineEmits<{
  connected: []
  disconnected: []
  error: [message: string]
  audioMute: [muted: boolean]
  videoMute: [muted: boolean]
  screenShare: [active: boolean]
  participants: [list: ParticipantState[]]
  chat: [msg: ChatMessage]
  qualityChanged: [quality: ConnectionQuality]
  rtt: [ms: number | null]  // Real WebRTC RTT (candidate-pair), null = noma'lum
  audioLevel: [level: number]  // Phase 5b.3 — lokal mic level (0–1)
  reaction: [data: ReactionEvent]  // Phase 5b.6
  handRaise: [data: HandRaiseEvent]  // Phase 5b.6
}>()

const room = ref<Room | null>(null)

// Local state
const localAudioMuted = ref(false)
const localVideoMuted = ref(false)
const localScreenSharing = ref(false)

function decodeMetadata(meta?: string): Record<string, unknown> {
  if (!meta) return {}
  try {
    return JSON.parse(meta) as Record<string, unknown>
  } catch {
    return {}
  }
}

function participantToState(p: Participant): ParticipantState {
  const meta = decodeMetadata(p.metadata)
  const audioTrack = p.getTrackPublication(Track.Source.Microphone)
  const videoTrack = p.getTrackPublication(Track.Source.Camera)
  const screenTrack = p.getTrackPublication(Track.Source.ScreenShare)
  return {
    identity: p.identity,
    name: p.name || p.identity,
    isLocal: p === (room.value?.localParticipant as unknown as Participant),
    isHost: meta.is_host === true,
    isMuted: !audioTrack || audioTrack.isMuted,
    videoMuted: !videoTrack || videoTrack.isMuted,
    isScreenSharing: !!screenTrack && !screenTrack.isMuted,
    isSpeaking: p.isSpeaking,
    metadata: meta,
  }
}

function refreshParticipants() {
  if (!room.value) return
  const list: ParticipantState[] = [
    participantToState(room.value.localParticipant as unknown as Participant),
  ]
  room.value.remoteParticipants.forEach((p) => {
    list.push(participantToState(p as unknown as Participant))
  })
  emit('participants', list)
}

async function connect() {
  if (room.value) return
  try {
    const r = new Room({
      adaptiveStream: true,
      dynacast: true,
    })

    r.on(RoomEvent.Connected, () => {
      emit('connected')
      refreshParticipants()
    })
    r.on(RoomEvent.Disconnected, () => {
      stopRtt()
      emit('disconnected')
    })
    r.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      if (state === ConnectionState.Disconnected) emit('disconnected')
    })
    r.on(RoomEvent.ParticipantConnected, refreshParticipants)
    r.on(RoomEvent.ParticipantDisconnected, refreshParticipants)
    r.on(RoomEvent.TrackPublished, refreshParticipants)
    r.on(RoomEvent.TrackUnpublished, refreshParticipants)
    r.on(RoomEvent.TrackSubscribed, refreshParticipants)
    r.on(RoomEvent.TrackUnsubscribed, refreshParticipants)
    r.on(RoomEvent.TrackMuted, refreshParticipants)
    r.on(RoomEvent.TrackUnmuted, refreshParticipants)
    r.on(RoomEvent.LocalTrackPublished, refreshParticipants)
    r.on(RoomEvent.LocalTrackUnpublished, refreshParticipants)
    r.on(RoomEvent.ActiveSpeakersChanged, refreshParticipants)
    r.on(
      RoomEvent.ConnectionQualityChanged,
      (quality: ConnectionQuality, participant?: Participant) => {
        if (participant === r.localParticipant) emit('qualityChanged', quality)
      },
    )
    r.on(
      RoomEvent.DataReceived,
      (payload: Uint8Array, participant?: RemoteParticipant) => {
        try {
          const text = new TextDecoder().decode(payload)
          const data = JSON.parse(text) as {
            kind: string
            text?: string
            emoji?: string
            up?: boolean
          }
          const from = participant?.identity ?? 'unknown'
          const nick = participant?.name ?? 'Mehmon'
          if (data.kind === 'chat' && data.text) {
            emit('chat', {
              from,
              nick,
              message: data.text,
              ts: Date.now(),
              isLocal: false,
            })
          } else if (data.kind === 'reaction' && data.emoji) {
            emit('reaction', { from, nick, emoji: data.emoji, ts: Date.now() })
          } else if (data.kind === 'hand_raise') {
            emit('handRaise', { from, nick, up: data.up === true })
          }
        } catch {
          // ignore
        }
      },
    )

    await r.connect(props.url, props.token)
    room.value = r

    // Real WebRTC RTT pollingni boshlaymiz (har 3s)
    stopRtt()
    rttTimer = setInterval(() => {
      readRtt().then((ms) => emit('rtt', ms))
    }, 3000)

    if (props.autoPublish) {
      try {
        if (props.audioOnly) {
          // Phase 5b.9 — audio-only mode (camera o'chirilgan, faqat mikrofon)
          await r.localParticipant.setMicrophoneEnabled(true)
          localVideoMuted.value = true
        } else {
          await r.localParticipant.enableCameraAndMicrophone()
        }
      } catch (mediaErr) {
        emit(
          'error',
          mediaErr instanceof Error ? mediaErr.message : String(mediaErr),
        )
      }
    }
    refreshParticipants()
    // Phase 5b.3 — local mic level meter (RAF loop)
    startLocalAudioMeter()
  } catch (e) {
    emit('error', e instanceof Error ? e.message : String(e))
  }
}

// === Phase 5b.3: Local audio level meter ===
let audioMeterCtx: AudioContext | null = null
let audioMeterAnalyser: AnalyserNode | null = null
let audioMeterSource: MediaStreamAudioSourceNode | null = null
let audioMeterRaf: number | null = null
let audioMeterBuf: Uint8Array | null = null
let audioMeterTrackId: string | null = null

function stopLocalAudioMeter() {
  if (audioMeterRaf !== null) {
    cancelAnimationFrame(audioMeterRaf)
    audioMeterRaf = null
  }
  try {
    audioMeterSource?.disconnect()
  } catch {
    // ignore
  }
  audioMeterSource = null
  audioMeterAnalyser = null
  if (audioMeterCtx) {
    audioMeterCtx.close().catch(() => {})
    audioMeterCtx = null
  }
  audioMeterTrackId = null
  audioMeterBuf = null
  emit('audioLevel', 0)
}

function startLocalAudioMeter() {
  if (!room.value) return
  const pub = room.value.localParticipant.getTrackPublication(
    Track.Source.Microphone,
  )
  const track = pub?.audioTrack?.mediaStreamTrack
  if (!track) {
    // Track hali tayyor emas — keyinroq qayta sinab ko'ramiz
    setTimeout(() => startLocalAudioMeter(), 500)
    return
  }
  // Agar bir xil track allaqachon kuzatilayotgan bo'lsa — qayta yaratmaymiz
  if (audioMeterTrackId === track.id && audioMeterRaf !== null) return
  stopLocalAudioMeter()
  audioMeterTrackId = track.id
  try {
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext
    if (!Ctx) return
    audioMeterCtx = new Ctx()
    const stream = new MediaStream([track])
    audioMeterSource = audioMeterCtx.createMediaStreamSource(stream)
    audioMeterAnalyser = audioMeterCtx.createAnalyser()
    audioMeterAnalyser.fftSize = 256
    audioMeterSource.connect(audioMeterAnalyser)
    audioMeterBuf = new Uint8Array(
      new ArrayBuffer(audioMeterAnalyser.frequencyBinCount),
    )
    let lastEmit = 0
    const tick = (now: number) => {
      if (!audioMeterAnalyser || !audioMeterBuf) return
      audioMeterAnalyser.getByteTimeDomainData(
        audioMeterBuf as Uint8Array<ArrayBuffer>,
      )
      // 10fps gacha emit qilamiz (CPU saqlash uchun)
      if (now - lastEmit > 100) {
        lastEmit = now
        let sum = 0
        for (let i = 0; i < audioMeterBuf.length; i++) {
          const v = (audioMeterBuf[i] - 128) / 128
          sum += v * v
        }
        const rms = Math.sqrt(sum / audioMeterBuf.length)
        emit('audioLevel', Math.min(1, rms * 3))  // amplify
      }
      audioMeterRaf = requestAnimationFrame(tick)
    }
    audioMeterRaf = requestAnimationFrame(tick)
  } catch (e) {
    console.warn('startLocalAudioMeter failed', e)
  }
}

// ---- Real WebRTC RTT (candidate-pair currentRoundTripTime) ----
let rttTimer: ReturnType<typeof setInterval> | null = null

function stopRtt() {
  if (rttTimer) {
    clearInterval(rttTimer)
    rttTimer = null
  }
}

async function readRtt(): Promise<number | null> {
  const r = room.value
  if (!r) return null
  try {
    // Mavjud trackni topamiz (lokal yoki remote) va WebRTC statistikasini o'qiymiz
    let track: unknown = null
    for (const pub of r.localParticipant.trackPublications.values()) {
      const tr = (pub as { track?: unknown }).track
      if (tr) { track = tr; break }
    }
    if (!track) {
      outer: for (const rp of r.remoteParticipants.values()) {
        for (const pub of rp.trackPublications.values()) {
          const tr = (pub as { track?: unknown }).track
          if (tr) { track = tr; break outer }
        }
      }
    }
    const getReport = (
      track as { getRTCStatsReport?: () => Promise<RTCStatsReport | undefined> } | null
    )?.getRTCStatsReport
    if (!track || typeof getReport !== 'function') return null
    const report = await getReport.call(track)
    if (!report) return null
    let rtt: number | null = null
    report.forEach(
      (s: { type?: string; state?: string; currentRoundTripTime?: number }) => {
        if (
          s.type === 'candidate-pair' &&
          s.state === 'succeeded' &&
          typeof s.currentRoundTripTime === 'number'
        ) {
          rtt = Math.round(s.currentRoundTripTime * 1000)
        }
      },
    )
    return rtt
  } catch {
    return null
  }
}

async function disconnect() {
  if (!room.value) return
  stopLocalAudioMeter()
  stopRtt()
  try {
    await room.value.disconnect()
  } catch {
    // ignore
  }
  room.value = null
}

onMounted(connect)
onBeforeUnmount(disconnect)

watch(
  () => [props.url, props.token],
  async () => {
    await disconnect()
    await connect()
  },
)

function attachTrack(
  el: HTMLMediaElement | null,
  identity: string,
  source: Track.Source = Track.Source.Camera,
) {
  if (!el || !room.value) return
  const p =
    room.value.localParticipant.identity === identity
      ? room.value.localParticipant
      : room.value.remoteParticipants.get(identity)
  if (!p) return
  const publication = p.getTrackPublication(source)
  if (publication?.track) {
    publication.track.attach(el as HTMLVideoElement)
  }
}

function detachTrack(
  el: HTMLMediaElement | null,
  identity: string,
  source: Track.Source = Track.Source.Camera,
) {
  if (!el || !room.value) return
  const p =
    room.value.localParticipant.identity === identity
      ? room.value.localParticipant
      : room.value.remoteParticipants.get(identity)
  if (!p) return
  const publication = p.getTrackPublication(source)
  if (publication?.track) {
    publication.track.detach(el as HTMLVideoElement)
  }
}

// AudioContext faqat user-gesture'dan keyin resume bo'lishi mumkin.
// Birinchi toggle'da room.startAudio() chaqirib uni "unblock" qilamiz.
async function ensureAudioStarted() {
  if (!room.value) return
  try {
    await room.value.startAudio()
  } catch {
    // ignore — ba'zi browserlarda kerak emas
  }
}

defineExpose({
  async toggleAudio() {
    if (!room.value) {
      emit('error', 'Room is not connected yet')
      return
    }
    await ensureAudioStarted()
    const newMuted = !localAudioMuted.value
    try {
      await room.value.localParticipant.setMicrophoneEnabled(!newMuted)
      localAudioMuted.value = newMuted
      emit('audioMute', newMuted)
      refreshParticipants()
      // Mute bo'lsa meterni to'xtatamiz, unmute bo'lsa qayta boshlaymiz
      if (newMuted) {
        stopLocalAudioMeter()
      } else {
        startLocalAudioMeter()
      }
    } catch (e) {
      emit(
        'error',
        e instanceof Error
          ? `Mikrofon: ${e.message}`
          : String(e),
      )
    }
  },
  async toggleVideo() {
    if (!room.value) {
      emit('error', 'Room is not connected yet')
      return
    }
    await ensureAudioStarted()
    const newMuted = !localVideoMuted.value
    try {
      await room.value.localParticipant.setCameraEnabled(!newMuted)
      localVideoMuted.value = newMuted
      emit('videoMute', newMuted)
      refreshParticipants()
    } catch (e) {
      emit(
        'error',
        e instanceof Error
          ? `Kamera: ${e.message}`
          : String(e),
      )
    }
  },
  async switchAudioInput(deviceId: string) {
    if (!room.value) return
    try {
      await room.value.switchActiveDevice('audioinput', deviceId)
      // Yangi track ulandi — meterni qayta boshlaymiz
      startLocalAudioMeter()
    } catch (e) {
      emit('error', e instanceof Error ? `Mic switch: ${e.message}` : String(e))
    }
  },
  async switchVideoInput(deviceId: string) {
    if (!room.value) return
    try {
      await room.value.switchActiveDevice('videoinput', deviceId)
    } catch (e) {
      emit('error', e instanceof Error ? `Cam switch: ${e.message}` : String(e))
    }
  },
  async switchAudioOutput(deviceId: string) {
    if (!room.value) return
    try {
      // Speaker switch — `setSinkId` qo'llab-quvvatlanmasa LiveKit silently fail qiladi
      await room.value.switchActiveDevice('audiooutput', deviceId)
    } catch (e) {
      emit('error', e instanceof Error ? `Speaker switch: ${e.message}` : String(e))
    }
  },
  async toggleScreenShare() {
    if (!room.value) {
      emit('error', 'Room is not connected yet')
      return
    }
    await ensureAudioStarted()
    const next = !localScreenSharing.value
    try {
      await room.value.localParticipant.setScreenShareEnabled(next)
      localScreenSharing.value = next
      emit('screenShare', next)
      refreshParticipants()
    } catch (e) {
      emit(
        'error',
        e instanceof Error
          ? `Ekran ulashish: ${e.message}`
          : String(e),
      )
    }
  },
  async sendChat(text: string) {
    if (!room.value || !text) return
    const data = new TextEncoder().encode(
      JSON.stringify({ kind: 'chat', text }),
    )
    await room.value.localParticipant.publishData(data, { reliable: true })
    emit('chat', {
      from: room.value.localParticipant.identity,
      nick: props.displayName || 'Siz',
      message: text,
      ts: Date.now(),
      isLocal: true,
    })
  },
  async sendReaction(emoji: string) {
    if (!room.value || !emoji) return
    const data = new TextEncoder().encode(
      JSON.stringify({ kind: 'reaction', emoji }),
    )
    try {
      await room.value.localParticipant.publishData(data, { reliable: false })
      // Lokal foydalanuvchining ham reaksiyasi qo'shilsin (echo)
      emit('reaction', {
        from: room.value.localParticipant.identity,
        nick: props.displayName || 'Siz',
        emoji,
        ts: Date.now(),
      })
    } catch (e) {
      emit('error', e instanceof Error ? `Reaction: ${e.message}` : String(e))
    }
  },
  async sendHandRaise(up: boolean) {
    if (!room.value) return
    const data = new TextEncoder().encode(
      JSON.stringify({ kind: 'hand_raise', up }),
    )
    try {
      await room.value.localParticipant.publishData(data, { reliable: true })
      // Lokal state'ni ham emit qilamiz (UI sync)
      emit('handRaise', {
        from: room.value.localParticipant.identity,
        nick: props.displayName || 'Siz',
        up,
      })
    } catch (e) {
      emit('error', e instanceof Error ? `Hand raise: ${e.message}` : String(e))
    }
  },
  hangup() {
    void disconnect()
  },
  attachTrack,
  detachTrack,
  getRoom: () => room.value,
  // Phase 5b.5 — Local camera resolution (network quality bar uchun)
  getLocalVideoSettings(): { width?: number; height?: number } | null {
    if (!room.value) return null
    const pub = room.value.localParticipant.getTrackPublication(
      Track.Source.Camera,
    )
    const track = pub?.videoTrack?.mediaStreamTrack
    if (!track) return null
    const s = track.getSettings()
    return { width: s.width, height: s.height }
  },
  // Phase 5b.9 — Retry permissions after denial
  async retryPermissions(includeCamera = true): Promise<boolean> {
    if (!room.value) {
      emit('error', 'Room is not connected yet')
      return false
    }
    try {
      await ensureAudioStarted()
      if (includeCamera) {
        await room.value.localParticipant.enableCameraAndMicrophone()
        localAudioMuted.value = false
        localVideoMuted.value = false
      } else {
        await room.value.localParticipant.setMicrophoneEnabled(true)
        localAudioMuted.value = false
      }
      emit('audioMute', false)
      if (includeCamera) emit('videoMute', false)
      refreshParticipants()
      startLocalAudioMeter()
      return true
    } catch (e) {
      emit(
        'error',
        e instanceof Error
          ? `Permission retry: ${e.message}`
          : String(e),
      )
      return false
    }
  },
  // Phase 5b.7 — Background blur (MediaPipe segmentation)
  async enableBackgroundBlur(amount = 10) {
    if (!room.value) {
      emit('error', 'Room is not connected yet')
      return
    }
    const pub = room.value.localParticipant.getTrackPublication(
      Track.Source.Camera,
    )
    const track = pub?.videoTrack as LocalVideoTrack | undefined
    if (!track) {
      emit('error', 'Camera track not available')
      return
    }
    try {
      const processor = BackgroundBlur(amount)
      await track.setProcessor(processor)
    } catch (e) {
      emit(
        'error',
        e instanceof Error
          ? `Background blur: ${e.message}`
          : String(e),
      )
    }
  },
  async disableBackgroundBlur() {
    if (!room.value) return
    const pub = room.value.localParticipant.getTrackPublication(
      Track.Source.Camera,
    )
    const track = pub?.videoTrack as LocalVideoTrack | undefined
    if (!track) return
    try {
      await track.stopProcessor()
    } catch (e) {
      emit(
        'error',
        e instanceof Error
          ? `Stop blur: ${e.message}`
          : String(e),
      )
    }
  },
  /** Phase 7a — host'ning lokal MediaStream tracklarini qaytaradi:
   *  - audio (mikrofon)
   *  - camera video (oldi kamera)
   *  - screen video (ekran share, agar mavjud bo'lsa)
   *  Composable canvas composite (screen + PiP camera) yasashda ishlatadi. */
  getLocalTracks(): {
    audio: MediaStreamTrack | null
    camera: MediaStreamTrack | null
    screen: MediaStreamTrack | null
  } {
    if (!room.value) return { audio: null, camera: null, screen: null }
    const lp = room.value.localParticipant

    const micPub = lp.getTrackPublication(Track.Source.Microphone)
    const camPub = lp.getTrackPublication(Track.Source.Camera)
    const screenPub = lp.getTrackPublication(Track.Source.ScreenShare)

    return {
      audio: micPub?.audioTrack?.mediaStreamTrack ?? null,
      camera: camPub?.videoTrack?.mediaStreamTrack ?? null,
      screen: screenPub?.videoTrack?.mediaStreamTrack ?? null,
    }
  },
  /** Backwards-compat: oldingi yagona MediaStream chiqaruvchi method
   *  (screen prioritet, aks holda kamera). Yangi composable foydalanmaydi. */
  getLocalRecordingStream(): MediaStream | null {
    if (!room.value) return null
    const lp = room.value.localParticipant
    const tracks: MediaStreamTrack[] = []
    const micPub = lp.getTrackPublication(Track.Source.Microphone)
    const micTrack = micPub?.audioTrack?.mediaStreamTrack
    if (micTrack) tracks.push(micTrack)
    const screenPub = lp.getTrackPublication(Track.Source.ScreenShare)
    const screenTrack = screenPub?.videoTrack?.mediaStreamTrack
    if (screenTrack) {
      tracks.push(screenTrack)
    } else {
      const camPub = lp.getTrackPublication(Track.Source.Camera)
      const camTrack = camPub?.videoTrack?.mediaStreamTrack
      if (camTrack) tracks.push(camTrack)
    }
    if (tracks.length === 0) return null
    return new MediaStream(tracks)
  },
})
</script>

<template>
  <div style="display: none"></div>
</template>
