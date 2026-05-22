/**
 * SCORM 1.2 + 2004 API bridge — Phase 11a.
 *
 * SCORM iframe child windowdan parent window'da `window.API` (1.2) yoki
 * `window.API_1484_11` (2004) global obyektni qidiradi. Bu composable
 * o'sha obyektni o'rnatadi va `LMSGetValue`/`LMSSetValue`/`LMSCommit`/
 * `LMSFinish` chaqiruvlarini backend'ga tarjima qiladi.
 *
 * Optimization: SetValue chaqiruvlari local cache'ga yig'iladi va LMSCommit
 * (yoki har 10s avto) backend'ga batch sifatida yuboriladi.
 *
 * Foydalanish:
 *   const bridge = useScormApi(attemptId, () => attempt.value?.cmi_data ?? {})
 *   bridge.install()  // window.API_1484_11 va window.API
 *   onUnmount(bridge.uninstall)
 */

import { scormApi } from '@shared/api/scorm'

type CmiData = Record<string, unknown>

const SCORM_FALSE = 'false'
const SCORM_TRUE = 'true'

// Standart SCORM 1.2 error codes
const ERR_NO_ERROR = '0'
const ERR_GENERAL_EXCEPTION = '101'

interface BridgeOptions {
  attemptId: number
  initialCmi: () => CmiData
  /** Auto-commit har N ms (default 30s) */
  autoCommitMs?: number
}

export function useScormApi(opts: BridgeOptions) {
  const { attemptId, initialCmi, autoCommitMs = 30_000 } = opts

  let cmi: CmiData = { ...initialCmi() }
  const pending: CmiData = {}  // SetValue dan keyin commit kutib turgan o'zgarishlar
  let initialized = false
  let lastError = ERR_NO_ERROR
  let autoCommitTimer: ReturnType<typeof setInterval> | null = null

  function getValue(key: string): string {
    if (!initialized) {
      lastError = '301'  // not initialized
      return ''
    }
    const v = cmi[key] ?? pending[key]
    if (v === undefined || v === null) {
      lastError = '201'  // data model element not implemented (SCORM 1.2 friendly)
      return ''
    }
    lastError = ERR_NO_ERROR
    return String(v)
  }

  function setValue(key: string, value: unknown): string {
    if (!initialized) {
      lastError = '301'
      return SCORM_FALSE
    }
    pending[key] = value
    cmi[key] = value
    lastError = ERR_NO_ERROR
    return SCORM_TRUE
  }

  async function commitInner(): Promise<boolean> {
    if (Object.keys(pending).length === 0) return true
    const payload = { ...pending }
    // Pendingni darhol tozalaymiz — keyin commit'da yangi o'zgarishlar yig'ilsin
    for (const k of Object.keys(payload)) delete pending[k]
    try {
      const updated = await scormApi.commit(attemptId, payload)
      // Backend cmi_data ni mergedolayotgan bo'lishi mumkin — yangilab qo'yamiz
      cmi = updated.cmi_data ?? cmi
      return true
    } catch (e) {
      console.error('[SCORM] commit failed', e)
      // Pendingga qaytarib qo'yamiz — keyingi safarda qayta urinish
      Object.assign(pending, payload)
      lastError = ERR_GENERAL_EXCEPTION
      return false
    }
  }

  function commit(): string {
    void commitInner()
    return SCORM_TRUE
  }

  function initialize(): string {
    if (initialized) {
      lastError = '101'  // already initialized
      return SCORM_FALSE
    }
    initialized = true
    lastError = ERR_NO_ERROR
    // Auto-commit boshlash
    if (autoCommitMs > 0) {
      autoCommitTimer = setInterval(() => void commitInner(), autoCommitMs)
    }
    return SCORM_TRUE
  }

  async function finish(): Promise<string> {
    if (!initialized) {
      lastError = '301'
      return SCORM_FALSE
    }
    if (autoCommitTimer) {
      clearInterval(autoCommitTimer)
      autoCommitTimer = null
    }
    // Yakuniy commit
    await commitInner()
    try {
      await scormApi.finish(attemptId)
    } catch (e) {
      console.error('[SCORM] finish failed', e)
    }
    initialized = false
    return SCORM_TRUE
  }

  function getLastError(): string {
    return lastError
  }

  function getErrorString(_code: string): string {
    return ''
  }

  function getDiagnostic(_code: string): string {
    return ''
  }

  // SCORM 1.2 API (legacy)
  const api12 = {
    LMSInitialize: (_arg: string) => initialize(),
    LMSGetValue: (key: string) => getValue(key),
    LMSSetValue: (key: string, value: unknown) => setValue(key, value),
    LMSCommit: (_arg: string) => commit(),
    LMSFinish: (_arg: string) => {
      void finish()
      return SCORM_TRUE
    },
    LMSGetLastError: () => getLastError(),
    LMSGetErrorString: (code: string) => getErrorString(code),
    LMSGetDiagnostic: (code: string) => getDiagnostic(code),
  }

  // SCORM 2004 API (4th edition)
  const api2004 = {
    Initialize: (_arg: string) => initialize(),
    GetValue: (key: string) => getValue(key),
    SetValue: (key: string, value: unknown) => setValue(key, value),
    Commit: (_arg: string) => commit(),
    Terminate: (_arg: string) => {
      void finish()
      return SCORM_TRUE
    },
    GetLastError: () => getLastError(),
    GetErrorString: (code: string) => getErrorString(code),
    GetDiagnostic: (code: string) => getDiagnostic(code),
  }

  function install(): void {
    // Ikkala versiyani ham yozamiz — SCORM child o'ziga kerakli versiyani topadi
    ;(window as unknown as { API: typeof api12 }).API = api12
    ;(window as unknown as { API_1484_11: typeof api2004 }).API_1484_11 = api2004
  }

  function uninstall(): void {
    if (autoCommitTimer) {
      clearInterval(autoCommitTimer)
      autoCommitTimer = null
    }
    delete (window as unknown as { API?: unknown }).API
    delete (window as unknown as { API_1484_11?: unknown }).API_1484_11
  }

  return {
    install,
    uninstall,
    commit: commitInner,
    finish,
    isInitialized: () => initialized,
  }
}
