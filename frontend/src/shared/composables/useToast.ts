/**
 * Phase 8a — Lightweight toast notifications.
 *
 *   toast.success('Saqlandi')
 *   toast.error('Xato yuz berdi')
 *   toast.info('Yangi xabar')
 *   toast.warning('Diqqat')
 *
 * App.vue ichida `<UiToastHost />` bo'lishi kerak.
 */
import { reactive } from 'vue'

export type ToastVariant = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  variant: ToastVariant
  message: string
  /** ms */
  duration: number
}

interface ToastState {
  items: ToastItem[]
}

export const toastState = reactive<ToastState>({ items: [] })

let nextId = 1

function push(variant: ToastVariant, message: string, duration = 3500) {
  const id = nextId++
  toastState.items.push({ id, variant, message, duration })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
  return id
}

export function dismiss(id: number) {
  const idx = toastState.items.findIndex((t) => t.id === id)
  if (idx !== -1) toastState.items.splice(idx, 1)
}

export const toast = {
  success: (msg: string, duration?: number) => push('success', msg, duration),
  error: (msg: string, duration?: number) => push('error', msg, duration ?? 5000),
  info: (msg: string, duration?: number) => push('info', msg, duration),
  warning: (msg: string, duration?: number) => push('warning', msg, duration),
}

export function useToast() {
  return { toast }
}
