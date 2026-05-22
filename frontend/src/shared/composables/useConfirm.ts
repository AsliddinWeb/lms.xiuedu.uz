/**
 * Phase 8a — Imperative confirm dialog (window.confirm replacement).
 *
 * Global singleton state. Foydalanish:
 *   const ok = await confirm({ title: '...', description: '...', variant: 'danger' })
 *   if (!ok) return
 *
 * App komponentida `<UiConfirmHost />` mavjud bo'lishi shart (App.vue ichida bir marta).
 */
import { reactive } from 'vue'

export interface ConfirmOptions {
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'danger'
  alertMode?: boolean
}

interface ConfirmState extends ConfirmOptions {
  open: boolean
  _resolve: ((value: boolean) => void) | null
}

export const confirmState = reactive<ConfirmState>({
  open: false,
  title: '',
  description: '',
  confirmLabel: '',
  cancelLabel: '',
  variant: 'default',
  alertMode: false,
  _resolve: null,
})

export function confirm(opts: ConfirmOptions): Promise<boolean> {
  // Agar avvalgi dialog ochiq bo'lsa, uni cancel qilamiz.
  if (confirmState._resolve) {
    confirmState._resolve(false)
  }
  confirmState.title = opts.title
  confirmState.description = opts.description ?? ''
  confirmState.confirmLabel = opts.confirmLabel ?? ''
  confirmState.cancelLabel = opts.cancelLabel ?? ''
  confirmState.variant = opts.variant ?? 'default'
  confirmState.alertMode = opts.alertMode ?? false
  confirmState.open = true
  return new Promise<boolean>((resolve) => {
    confirmState._resolve = resolve
  })
}

export function resolveConfirm(result: boolean) {
  const r = confirmState._resolve
  confirmState._resolve = null
  confirmState.open = false
  if (r) r(result)
}

/**
 * Composable wrapper — vue.use() qilmasdan ham komponentlardan ishlatish uchun.
 */
export function useConfirm() {
  return { confirm }
}
