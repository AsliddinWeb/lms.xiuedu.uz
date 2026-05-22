/**
 * Phase 9c — Web Speech API wrapper (real-time subtitle).
 *
 * `SpeechRecognition` API faqat Chrome/Edge'da bor. Boshqa brauzerlar uchun
 * `supported` false bo'ladi va caption ish bermaydi (kelajakda Whisper API).
 *
 * Mantiq:
 *   - `start(lang)` chaqirilsa, recognition davom etadi
 *   - Har "result" event'i (interim + final) emit qilinadi
 *   - Continuous mode + interim results yoqilgan
 *   - End event'ida (network error / timeout) avtomatik qayta start qilinadi
 *
 * Tarjima: faqat tanigan tilini qaytaradi (browser TTS). Translation kelajakda.
 */

import { onBeforeUnmount, ref } from 'vue'

export interface CaptionSegment {
  text: string
  isFinal: boolean
  startMs: number
  endMs: number
  lang: string
}

// Web Speech API TypeScript declarations are missing in standard lib.
// We define a minimal interface for what we actually use.
interface SRResult {
  isFinal: boolean
  [index: number]: { transcript: string }
}
interface SREvent {
  resultIndex: number
  results: { length: number; [index: number]: SRResult }
}
interface SRErrorEvent {
  error: string
}
interface SRInstance {
  continuous: boolean
  interimResults: boolean
  lang: string
  maxAlternatives: number
  onresult: ((ev: SREvent) => void) | null
  onerror: ((ev: SRErrorEvent) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}
type SRCtor = new () => SRInstance

interface SRWindow {
  SpeechRecognition?: SRCtor
  webkitSpeechRecognition?: SRCtor
}

function getRecognitionCtor(): SRCtor | null {
  const w = window as unknown as SRWindow
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

export function useSpeechRecognition() {
  const supported = ref(getRecognitionCtor() !== null)
  const listening = ref(false)
  const lastInterim = ref('')
  const error = ref<string | null>(null)

  let recognition: SRInstance | null = null
  let sessionStartTime: number | null = null
  let currentLang = 'uz-UZ'
  let stoppedByUser = false
  let onSegmentCb: ((seg: CaptionSegment) => void) | null = null

  function start(lang = 'uz-UZ', onSegment?: (seg: CaptionSegment) => void): void {
    if (!supported.value) {
      error.value = 'speech_recognition_unsupported'
      return
    }
    const Ctor = getRecognitionCtor()
    if (!Ctor) return
    if (listening.value) return

    onSegmentCb = onSegment ?? null
    currentLang = lang
    stoppedByUser = false
    sessionStartTime = Date.now()

    recognition = new Ctor()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = lang
    recognition.maxAlternatives = 1

    recognition.onresult = (ev: SREvent) => {
      const now = Date.now()
      const startMs = sessionStartTime ? now - sessionStartTime - 1000 : 0
      const endMs = sessionStartTime ? now - sessionStartTime : 0
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i]
        const text = r[0].transcript.trim()
        if (!text) continue
        const seg: CaptionSegment = {
          text,
          isFinal: r.isFinal,
          startMs: Math.max(0, startMs),
          endMs: Math.max(startMs + 100, endMs),
          lang: currentLang,
        }
        if (!r.isFinal) {
          lastInterim.value = text
        } else {
          lastInterim.value = ''
        }
        onSegmentCb?.(seg)
      }
    }

    recognition.onerror = (ev: SRErrorEvent) => {
      // "no-speech" tez-tez chiqadi — error emas
      if (ev.error === 'no-speech' || ev.error === 'audio-capture') return
      error.value = ev.error
    }

    recognition.onend = () => {
      listening.value = false
      // Auto-restart agar user to'xtatmagan bo'lsa
      if (!stoppedByUser && recognition) {
        try {
          recognition.start()
          listening.value = true
        } catch {
          // ignore — start failed (e.g. already running)
        }
      }
    }

    try {
      recognition.start()
      listening.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'recognition_start_failed'
    }
  }

  function stop(): void {
    stoppedByUser = true
    if (recognition) {
      try {
        recognition.stop()
      } catch {
        // ignore
      }
      recognition = null
    }
    listening.value = false
    lastInterim.value = ''
    sessionStartTime = null
  }

  function setLang(lang: string): void {
    if (lang === currentLang) return
    const wasListening = listening.value
    stop()
    if (wasListening) start(lang, onSegmentCb ?? undefined)
  }

  onBeforeUnmount(() => stop())

  return {
    supported,
    listening,
    lastInterim,
    error,
    start,
    stop,
    setLang,
  }
}
