/**
 * Phase 7a — Live recording composable (canvas-composite + MediaRecorder).
 *
 * Pedagog REC tugmasini bossa:
 *   1. Backend'da yangi recording row ochiladi (status=recording)
 *   2. LiveKit local tracklar olinadi: audio + camera + screen (agar share bo'lsa)
 *   3. Off-screen <canvas> 1280x720 yaratiladi; har frame'da:
 *        - Screen video (bor bo'lsa) — to'liq fon
 *        - Camera video (bor bo'lsa) — PiP (~22% kenglik, pastki-o'ng)
 *        - Faqat kamera bo'lsa — to'liq fon
 *   4. canvas.captureStream(30) + audio track → MediaStream → MediaRecorder
 *   5. Stop bosilsa → Blob merge → backend'ga upload + canvas loop to'xtatiladi
 *
 * Bu yondashuv talaba ekran ulashganda ham, kamerasi yoqilganda ham,
 * ikkalasi bilan birga ham bir xil ishlaydi.
 */

import { computed, onBeforeUnmount, ref } from 'vue'

import { liveRecordingsApi, type LiveRecording } from '@shared/api/live'

const PREFERRED_MIME_TYPES = [
  'video/webm;codecs=vp9,opus',
  'video/webm;codecs=vp8,opus',
  'video/webm',
  'video/mp4',
]

const CANVAS_W = 1280
const CANVAS_H = 720
// Phase 7a polish — dumaloq PiP, pastki-chap, professional ring + soya
const PIP_D = 200 // diametr
const PIP_MARGIN = 28

function pickMime(): string {
  if (typeof MediaRecorder === 'undefined') return 'video/webm'
  for (const mime of PREFERRED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mime)) return mime
  }
  return 'video/webm'
}

export interface LocalTracks {
  audio: MediaStreamTrack | null
  camera: MediaStreamTrack | null
  screen: MediaStreamTrack | null
}

export type GetLocalTracks = () => LocalTracks

interface CompositeRig {
  canvas: HTMLCanvasElement
  ctx: CanvasRenderingContext2D
  cameraVideo: HTMLVideoElement
  screenVideo: HTMLVideoElement
  stop: () => void
}

function buildCompositeRig(getTracks: GetLocalTracks): CompositeRig | null {
  const canvas = document.createElement('canvas')
  canvas.width = CANVAS_W
  canvas.height = CANVAS_H
  const ctxOrNull = canvas.getContext('2d')
  if (!ctxOrNull) return null
  const ctx: CanvasRenderingContext2D = ctxOrNull

  // Off-screen video elements'ni DOM'ga qo'shamiz — Chrome detached yoki
  // -9999px off-screen video uchun frame ishlab chiqarmaydi (yoki ba'zan
  // muzlatib qo'yadi). Shu sababli 1x1 pixel, fully transparent, lekin
  // viewport ichida joylashtirib qo'yamiz.
  const hidden = document.createElement('div')
  hidden.style.position = 'fixed'
  hidden.style.top = '0'
  hidden.style.left = '0'
  hidden.style.width = '1px'
  hidden.style.height = '1px'
  hidden.style.opacity = '0.01'
  hidden.style.pointerEvents = 'none'
  hidden.style.zIndex = '-1'
  document.body.appendChild(hidden)

  const cameraVideo = document.createElement('video')
  cameraVideo.muted = true
  cameraVideo.autoplay = true
  cameraVideo.playsInline = true
  hidden.appendChild(cameraVideo)

  const screenVideo = document.createElement('video')
  screenVideo.muted = true
  screenVideo.autoplay = true
  screenVideo.playsInline = true
  hidden.appendChild(screenVideo)

  function attach(): void {
    const t = getTracks()
    const camCurrent = cameraVideo.srcObject as MediaStream | null
    const camCurrentId = camCurrent?.getVideoTracks()[0]?.id
    if (t.camera && t.camera.id !== camCurrentId) {
      cameraVideo.srcObject = new MediaStream([t.camera])
      cameraVideo.play().catch(() => null)
    } else if (!t.camera && camCurrent) {
      cameraVideo.srcObject = null
    }
    const scrCurrent = screenVideo.srcObject as MediaStream | null
    const scrCurrentId = scrCurrent?.getVideoTracks()[0]?.id
    if (t.screen && t.screen.id !== scrCurrentId) {
      screenVideo.srcObject = new MediaStream([t.screen])
      screenVideo.play().catch(() => null)
    } else if (!t.screen && scrCurrent) {
      screenVideo.srcObject = null
    }
  }
  attach()

  // Background fill (in case neither source ready yet)
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)

  let intervalId: ReturnType<typeof setInterval> | null = null
  let lastAttach = 0
  let lastPlayCheck = 0

  // Defensive — agar brauzer off-screen video'ni pause qilsa, qayta yoqamiz.
  function ensurePlaying(v: HTMLVideoElement): void {
    if (v.srcObject && v.paused) {
      v.play().catch(() => null)
    }
  }

  // Tab orqaga o'tsa rAF butunlay to'xtaydi — Page Visibility listener
  // orqali ekran/kamera video'ni force-play qilamiz.
  const onVisibilityChange = (): void => {
    ensurePlaying(cameraVideo)
    ensurePlaying(screenVideo)
  }
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('focus', onVisibilityChange)
  window.addEventListener('blur', onVisibilityChange)

  function drawCircularPip(
    src: HTMLVideoElement,
    cx: number,
    cy: number,
    radius: number,
  ): void {
    const sw = src.videoWidth
    const sh = src.videoHeight
    if (sw === 0 || sh === 0) return
    // cover crop — kameraning markazidagi kvadrat
    const side = Math.min(sw, sh)
    const sx = (sw - side) / 2
    const sy = (sh - side) / 2

    // 1) Outer soya
    ctx.save()
    ctx.shadowColor = 'rgba(0,0,0,0.45)'
    ctx.shadowBlur = 18
    ctx.shadowOffsetY = 4
    ctx.fillStyle = 'rgba(0,0,0,0.001)' // soyani render qilish uchun
    ctx.beginPath()
    ctx.arc(cx, cy, radius + 4, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()

    // 2) White ring
    ctx.save()
    ctx.fillStyle = '#ffffff'
    ctx.beginPath()
    ctx.arc(cx, cy, radius + 4, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()

    // 3) Camera kadr — circular clip
    ctx.save()
    ctx.beginPath()
    ctx.arc(cx, cy, radius, 0, Math.PI * 2)
    ctx.closePath()
    ctx.clip()
    ctx.drawImage(
      src,
      sx,
      sy,
      side,
      side,
      cx - radius,
      cy - radius,
      radius * 2,
      radius * 2,
    )
    ctx.restore()
  }

  const render = () => {
    const now = performance.now()

    // Har 1s da track'larni qayta tekshiramiz (recording paytida screen
    // qo'shilsa yoki olib tashlansa)
    if (now - lastAttach > 1000) {
      attach()
      lastAttach = now
    }
    // Har 500ms da video element pause bo'lganligini tekshiramiz (kadr muzlamasligi uchun)
    if (now - lastPlayCheck > 500) {
      ensurePlaying(cameraVideo)
      ensurePlaying(screenVideo)
      lastPlayCheck = now
    }

    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)

    const hasScreen = screenVideo.videoWidth > 0 && screenVideo.readyState >= 2
    const hasCamera = cameraVideo.videoWidth > 0 && cameraVideo.readyState >= 2

    if (hasScreen) {
      // Fit screen (contain) within canvas
      const sw = screenVideo.videoWidth
      const sh = screenVideo.videoHeight
      const scale = Math.min(CANVAS_W / sw, CANVAS_H / sh)
      const dw = sw * scale
      const dh = sh * scale
      const dx = (CANVAS_W - dw) / 2
      const dy = (CANVAS_H - dh) / 2
      ctx.drawImage(screenVideo, dx, dy, dw, dh)

      // Camera PiP — pastki-chap, dumaloq
      if (hasCamera) {
        const radius = PIP_D / 2
        const cx = PIP_MARGIN + radius
        const cy = CANVAS_H - PIP_MARGIN - radius
        drawCircularPip(cameraVideo, cx, cy, radius)
      }
    } else if (hasCamera) {
      // Camera fullscreen (cover)
      const cw = cameraVideo.videoWidth
      const ch = cameraVideo.videoHeight
      const targetAspect = CANVAS_W / CANVAS_H
      const srcAspect = cw / ch
      let sx = 0
      let sy = 0
      let sW = cw
      let sH = ch
      if (srcAspect > targetAspect) {
        sW = ch * targetAspect
        sx = (cw - sW) / 2
      } else {
        sH = cw / targetAspect
        sy = (ch - sH) / 2
      }
      ctx.drawImage(cameraVideo, sx, sy, sW, sH, 0, 0, CANVAS_W, CANVAS_H)
    }
  }

  // setInterval — rAF emas, chunki rAF tab fokusda bo'lmaganda to'xtaydi.
  // setInterval esa MediaRecorder faol bo'lganda ham 33ms interval'da fire'lab turadi.
  intervalId = setInterval(render, 33)

  const stop = (): void => {
    if (intervalId !== null) clearInterval(intervalId)
    intervalId = null
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('focus', onVisibilityChange)
    window.removeEventListener('blur', onVisibilityChange)
    cameraVideo.srcObject = null
    screenVideo.srcObject = null
    hidden.remove()
  }

  return { canvas, ctx, cameraVideo, screenVideo, stop }
}

export function useLiveRecorder() {
  const recording = ref<LiveRecording | null>(null)
  const isRecording = ref(false)
  const isUploading = ref(false)
  const error = ref<string | null>(null)
  const startedAt = ref<number | null>(null)
  const elapsedSec = ref(0)

  let recorder: MediaRecorder | null = null
  let chunks: Blob[] = []
  let tickTimer: ReturnType<typeof setInterval> | null = null
  let rig: CompositeRig | null = null
  let canvasStream: MediaStream | null = null

  const sizeBytesRef = ref(0)
  // ~700MB dan oshsa brauzer xotirasi xavf ostida — host'ni ogohlantiramiz
  const sizeWarning = computed(() => sizeBytesRef.value > 700 * 1024 * 1024)

  async function start(sessionId: number, getTracks: GetLocalTracks): Promise<void> {
    if (isRecording.value) return
    error.value = null

    try {
      recording.value = await liveRecordingsApi.start(sessionId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'recording_start_failed'
      return
    }

    try {
      rig = buildCompositeRig(getTracks)
      if (!rig) throw new Error('canvas_not_supported')

      const videoStream = rig.canvas.captureStream(30)
      canvasStream = videoStream

      const initial = getTracks()
      const combined = new MediaStream()
      videoStream.getVideoTracks().forEach((t) => combined.addTrack(t))
      if (initial.audio) combined.addTrack(initial.audio)

      const mime = pickMime()
      chunks = []
      recorder = new MediaRecorder(combined, { mimeType: mime, videoBitsPerSecond: 2_500_000 })
      recorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunks.push(ev.data)
      }
      recorder.onerror = (ev) => {
        const e = ev as ErrorEvent
        error.value = e.error?.message ?? 'recording_error'
      }
      recorder.start(60_000)
      isRecording.value = true
      startedAt.value = Date.now()
      tickTimer = setInterval(() => {
        if (startedAt.value) {
          elapsedSec.value = Math.floor((Date.now() - startedAt.value) / 1000)
          sizeBytesRef.value = chunks.reduce((acc, c) => acc + c.size, 0)
        }
      }, 1000)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'mediarecorder_unsupported'
      rig?.stop()
      rig = null
      canvasStream?.getTracks().forEach((t) => t.stop())
      canvasStream = null
      recorder = null
      isRecording.value = false
    }
  }

  async function stop(): Promise<LiveRecording | null> {
    if (!recorder || !isRecording.value) return null
    isRecording.value = false
    if (tickTimer) {
      clearInterval(tickTimer)
      tickTimer = null
    }

    const r = recorder
    recorder = null
    const rec = recording.value
    const duration = elapsedSec.value

    await new Promise<void>((resolve) => {
      r.onstop = () => resolve()
      try {
        r.stop()
      } catch {
        resolve()
      }
    })

    // Stop canvas loop + capture stream tracks
    rig?.stop()
    rig = null
    canvasStream?.getTracks().forEach((t) => t.stop())
    canvasStream = null

    if (!rec || chunks.length === 0) {
      error.value = 'no_chunks'
      return null
    }

    const blob = new Blob(chunks, { type: r.mimeType || 'video/webm' })
    chunks = []

    isUploading.value = true
    try {
      const final = await liveRecordingsApi.upload(rec.id, blob, duration)
      recording.value = final
      return final
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'upload_failed'
      return null
    } finally {
      isUploading.value = false
      startedAt.value = null
      elapsedSec.value = 0
    }
  }

  function reset() {
    if (isRecording.value && recorder) {
      try {
        recorder.stop()
      } catch {
        // ignore
      }
    }
    if (tickTimer) clearInterval(tickTimer)
    tickTimer = null
    rig?.stop()
    rig = null
    canvasStream?.getTracks().forEach((t) => t.stop())
    canvasStream = null
    recorder = null
    chunks = []
    recording.value = null
    isRecording.value = false
    isUploading.value = false
    error.value = null
    startedAt.value = null
    elapsedSec.value = 0
    sizeBytesRef.value = 0
  }

  onBeforeUnmount(() => {
    reset()
  })

  return {
    recording,
    isRecording,
    isUploading,
    error,
    elapsedSec,
    sizeBytes: sizeBytesRef,
    sizeWarning,
    start,
    stop,
    reset,
  }
}
