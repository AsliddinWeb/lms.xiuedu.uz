/**
 * Phase 9a — face-api.js (TFLite) integratsiya.
 *
 * 3 ta model yuklanadi (~7MB):
 *   - tiny_face_detector — yuz bbox + count (190KB, eng tez)
 *   - face_landmark_68    — 68 ta yuz nuqtasi (350KB)
 *   - face_recognition    — 128-D yuz descriptor (6.4MB)
 *
 * API:
 *   loadModels()         — birinchi chaqirilganda fetch (lazy)
 *   detect(video)        — { faceCount, descriptor }  → snapshot uchun
 *   match(refDescriptor, currentDescriptor) → 0..1 cosine similarity
 *
 * Modellar `/face-api/models/` dan serve qilinadi (frontend/public/face-api/models/).
 */

import * as faceapi from 'face-api.js'
import { ref } from 'vue'

const MODELS_PATH = '/face-api/models'

let modelsPromise: Promise<void> | null = null

export function useFaceDetection() {
  const ready = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadModels(): Promise<void> {
    if (ready.value) return
    if (modelsPromise) {
      await modelsPromise
      ready.value = true
      return
    }
    loading.value = true
    error.value = null
    modelsPromise = (async () => {
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_PATH),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_PATH),
        faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_PATH),
      ])
    })()
    try {
      await modelsPromise
      ready.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'face_models_load_failed'
      modelsPromise = null
      throw e
    } finally {
      loading.value = false
    }
  }

  /** Bitta yuzni topib descriptor + yuzlar sonini qaytaradi. */
  async function detectWithDescriptor(
    src: HTMLVideoElement | HTMLCanvasElement | HTMLImageElement,
  ): Promise<{ faceCount: number; descriptor: Float32Array | null }> {
    if (!ready.value) await loadModels()
    const options = new faceapi.TinyFaceDetectorOptions({
      inputSize: 320,
      scoreThreshold: 0.5,
    })
    // First pass — count all faces (cheap)
    const detections = await faceapi.detectAllFaces(src, options)
    const faceCount = detections.length
    if (faceCount === 0) return { faceCount: 0, descriptor: null }
    // Pick the largest face for descriptor
    let best = detections[0]
    let bestArea = best.box.width * best.box.height
    for (const d of detections) {
      const area = d.box.width * d.box.height
      if (area > bestArea) {
        best = d
        bestArea = area
      }
    }
    const full = await faceapi
      .detectSingleFace(src, options)
      .withFaceLandmarks()
      .withFaceDescriptor()
    return {
      faceCount,
      descriptor: full?.descriptor ?? null,
    }
  }

  /** Faqat yuzlar sonini qaytaradi (descriptor'siz, tezroq). */
  async function detectCount(
    src: HTMLVideoElement | HTMLCanvasElement | HTMLImageElement,
  ): Promise<number> {
    if (!ready.value) await loadModels()
    const options = new faceapi.TinyFaceDetectorOptions({
      inputSize: 320,
      scoreThreshold: 0.5,
    })
    const detections = await faceapi.detectAllFaces(src, options)
    return detections.length
  }

  /** Phase 9b — gaze (yaw + pitch) hisoblash, 68 ta yuz nuqtasidan.
   *
   *  yaw  > 0  → bosh o'ngga qaragan (xayolan)
   *  pitch> 0  → bosh pastga qaragan
   *  faceCount qaytariladi (0 → gaze hisoblanmaydi). */
  async function detectGaze(
    src: HTMLVideoElement | HTMLCanvasElement | HTMLImageElement,
  ): Promise<{ faceCount: number; yaw: number; pitch: number } | null> {
    if (!ready.value) await loadModels()
    const options = new faceapi.TinyFaceDetectorOptions({
      inputSize: 320,
      scoreThreshold: 0.5,
    })
    const result = await faceapi
      .detectSingleFace(src, options)
      .withFaceLandmarks()
    if (!result) {
      // Yuz topilmadi — faceCount aniqlash uchun all detection
      const all = await faceapi.detectAllFaces(src, options)
      return { faceCount: all.length, yaw: 0, pitch: 0 }
    }
    const positions = result.landmarks.positions
    // Nose tip: index 30, eye centers: averages of 36..41 va 42..47
    const noseTip = positions[30]
    const leftEye = average(positions.slice(36, 42))
    const rightEye = average(positions.slice(42, 48))
    const eyeMidX = (leftEye.x + rightEye.x) / 2
    const eyeMidY = (leftEye.y + rightEye.y) / 2
    const eyeDist = Math.abs(rightEye.x - leftEye.x) || 1
    // Yaw: nose displacement normalizatsiyalangan
    const yaw = (noseTip.x - eyeMidX) / (eyeDist / 2)
    // Pitch: nose-eye vertical distance vs typical ratio
    const noseEyeDist = noseTip.y - eyeMidY
    const expected = eyeDist * 0.85
    const pitch = (noseEyeDist - expected) / Math.max(expected, 1)
    return { faceCount: 1, yaw, pitch }
  }

  function average(points: { x: number; y: number }[]): { x: number; y: number } {
    if (points.length === 0) return { x: 0, y: 0 }
    let sx = 0
    let sy = 0
    for (const p of points) {
      sx += p.x
      sy += p.y
    }
    return { x: sx / points.length, y: sy / points.length }
  }

  /** Reference descriptor bilan hozirgi descriptor o'rtasidagi cosine similarity.
   *  face-api.js euclidean distance qaytaradi (0 = bir xil, ~1.0 = farqli);
   *  shu sababli 1 - normalized_distance qaytaramiz (0..1, yuqori = o'xshash).
   *
   *  Asosiy threshold: face-api.js spec'da ~0.6 distance = "different people".
   *  Demak match_score = 1 - min(distance, 1) → 0.4 dan past bo'lsa boshqa odam. */
  function match(ref: Float32Array, current: Float32Array): number {
    const distance = faceapi.euclideanDistance(ref, current)
    const clamped = Math.min(distance, 1)
    return 1 - clamped
  }

  /** Float32Array → array<number> (JSON safe, localStorage'ga saqlash uchun). */
  function descriptorToJSON(d: Float32Array): number[] {
    return Array.from(d)
  }

  function descriptorFromJSON(arr: number[]): Float32Array {
    return Float32Array.from(arr)
  }

  return {
    ready,
    loading,
    error,
    loadModels,
    detectWithDescriptor,
    detectCount,
    detectGaze,
    match,
    descriptorToJSON,
    descriptorFromJSON,
  }
}
