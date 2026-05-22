/**
 * Phase 6f / 9a — Proctoring composable.
 *
 * Bitta joyga to'plangan: kamera stream, periodic snapshot upload,
 * event reporter (anti-cheat + face). Phase 9a'da `useFaceDetection`
 * bilan integratsiya: har snapshot uchun haqiqiy `face_count` va
 * (reference descriptor berilgan bo'lsa) `face_match_score`.
 */

import { onBeforeUnmount, ref } from 'vue'

import { proctoringApi, type ProctoringSeverity } from '@shared/api/proctoring'
import { useFaceDetection } from '@user/composables/useFaceDetection'

interface UseProctoringOptions {
  attemptId: number
  snapshotIntervalMs?: number  // default 30000
  faceReferenceDescriptor?: Float32Array | null  // lobby'dan kelgan reference
  gazeIntervalMs?: number  // default 2000 (Phase 9b)
  gazeOffSustainMs?: number  // default 10000 — shuncha vaqt off-screen bo'lsa event
}

const SNAPSHOT_W = 320
const SNAPSHOT_H = 240

export function useProctoring(opts: UseProctoringOptions) {
  const snapshotMs = opts.snapshotIntervalMs ?? 30000
  const gazeMs = opts.gazeIntervalMs ?? 2000
  const gazeOffSustainMs = opts.gazeOffSustainMs ?? 10000
  const refDescriptor = opts.faceReferenceDescriptor ?? null

  const stream = ref<MediaStream | null>(null)
  const videoEl = ref<HTMLVideoElement | null>(null)
  const canvasEl = ref<HTMLCanvasElement | null>(null)
  const lastSnapshotAt = ref<number | null>(null)
  const snapshotsUploaded = ref(0)
  const eventsSent = ref(0)
  const lastError = ref<string | null>(null)
  const lastFaceCount = ref<number | null>(null)
  const lastFaceMatch = ref<number | null>(null)
  const lastGazeYaw = ref<number | null>(null)
  const lastGazePitch = ref<number | null>(null)

  // Phase 9a — face detection (lazy load when proctoring starts)
  const face = useFaceDetection()
  // Load models in background — non-blocking
  face.loadModels().catch(() => null)

  let snapshotTimer: ReturnType<typeof setInterval> | null = null
  let gazeTimer: ReturnType<typeof setInterval> | null = null

  // Phase 9b — gaze state machine
  // off-screen detected at this timestamp (null = currently on-screen)
  let offScreenStartedAt: number | null = null
  let lastGazeOffEventAt = 0  // debounce — bir marta event yuborilgach 30s tinch turamiz
  const GAZE_OFF_DEBOUNCE_MS = 30000
  const YAW_THRESHOLD = 0.45
  const PITCH_THRESHOLD_DOWN = 0.35
  const PITCH_THRESHOLD_UP = -0.4

  async function start(video: HTMLVideoElement) {
    videoEl.value = video
    const canvas = document.createElement('canvas')
    canvas.width = SNAPSHOT_W
    canvas.height = SNAPSHOT_H
    canvasEl.value = canvas
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: SNAPSHOT_W * 2 }, height: { ideal: SNAPSHOT_H * 2 } },
        audio: false,
      })
      stream.value = s
      video.srcObject = s
      await video.play()
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : 'camera_blocked'
      return
    }
    snapshotTimer = setInterval(() => {
      captureAndUpload().catch(() => null)
    }, snapshotMs)

    // Phase 9b — gaze tracking timer (2s default)
    gazeTimer = setInterval(() => {
      pollGaze().catch(() => null)
    }, gazeMs)
  }

  function stop() {
    if (snapshotTimer) {
      clearInterval(snapshotTimer)
      snapshotTimer = null
    }
    if (gazeTimer) {
      clearInterval(gazeTimer)
      gazeTimer = null
    }
    offScreenStartedAt = null
    stream.value?.getTracks().forEach((t) => t.stop())
    stream.value = null
    if (videoEl.value) videoEl.value.srcObject = null
  }

  async function pollGaze(): Promise<void> {
    if (!videoEl.value || !face.ready.value) return
    const result = await face.detectGaze(videoEl.value).catch(() => null)
    if (!result) return
    lastGazeYaw.value = result.yaw
    lastGazePitch.value = result.pitch

    // Faqat aniq 1 yuz bo'lganda gaze hisoblaymiz
    if (result.faceCount !== 1) {
      // Yuz yo'q — gaze state'ni reset qilamiz
      offScreenStartedAt = null
      return
    }

    const offScreen =
      Math.abs(result.yaw) > YAW_THRESHOLD ||
      result.pitch > PITCH_THRESHOLD_DOWN ||
      result.pitch < PITCH_THRESHOLD_UP

    const now = Date.now()
    if (offScreen) {
      if (offScreenStartedAt === null) {
        offScreenStartedAt = now
      } else if (
        now - offScreenStartedAt >= gazeOffSustainMs &&
        now - lastGazeOffEventAt >= GAZE_OFF_DEBOUNCE_MS
      ) {
        // Sustained off-screen — event yuborish
        lastGazeOffEventAt = now
        await reportEvent('gaze_off', 'warning', {
          yaw: Number(result.yaw.toFixed(2)),
          pitch: Number(result.pitch.toFixed(2)),
          duration_ms: now - offScreenStartedAt,
        })
      }
    } else {
      if (offScreenStartedAt !== null) {
        offScreenStartedAt = null
        // Faqat event yuborilgan bo'lsa, qaytish faktini ham log qilamiz
        if (now - lastGazeOffEventAt < GAZE_OFF_DEBOUNCE_MS) {
          await reportEvent('gaze_returned', 'info', null)
        }
      }
    }
  }

  async function captureAndUpload(): Promise<void> {
    if (!videoEl.value || !canvasEl.value || !stream.value) return
    const v = videoEl.value
    const c = canvasEl.value
    const ctx = c.getContext('2d')
    if (!ctx) return
    ctx.drawImage(v, 0, 0, c.width, c.height)

    // Phase 9a — face detection in parallel with blob encoding
    let faceCount: number | null = null
    let faceMatch: number | null = null
    if (face.ready.value) {
      try {
        if (refDescriptor) {
          const r = await face.detectWithDescriptor(c)
          faceCount = r.faceCount
          if (r.descriptor && refDescriptor) {
            faceMatch = face.match(refDescriptor, r.descriptor)
          }
        } else {
          faceCount = await face.detectCount(c)
        }
      } catch {
        // face-api.js failure — proceed without
      }
    }
    lastFaceCount.value = faceCount
    lastFaceMatch.value = faceMatch

    const blob = await new Promise<Blob | null>((resolve) =>
      c.toBlob(resolve, 'image/jpeg', 0.7),
    )
    if (!blob) return
    try {
      await proctoringApi.snapshot(opts.attemptId, blob, {
        face_count: faceCount,
        face_match_score: faceMatch,
        width: c.width,
        height: c.height,
      })
      snapshotsUploaded.value++
      lastSnapshotAt.value = Date.now()
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : 'snapshot_failed'
    }
  }

  async function reportEvent(
    eventType: string,
    severity: ProctoringSeverity = 'info',
    metadata: Record<string, unknown> | null = null,
  ): Promise<void> {
    try {
      await proctoringApi.event(opts.attemptId, {
        event_type: eventType,
        severity,
        metadata,
        occurred_at: new Date().toISOString(),
      })
      eventsSent.value++
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : 'event_failed'
    }
  }

  onBeforeUnmount(() => {
    stop()
  })

  return {
    stream,
    snapshotsUploaded,
    eventsSent,
    lastSnapshotAt,
    lastError,
    start,
    stop,
    captureAndUpload,
    reportEvent,
  }
}
