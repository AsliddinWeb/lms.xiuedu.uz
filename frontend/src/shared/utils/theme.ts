/**
 * Tema utilita'lari — light/dark/system tristate, localStorage'da saqlanadi.
 * `dark` klass `<html>` ga qo'shiladi/olib tashlanadi (Tailwind darkMode: 'class').
 *
 * FOUC oldini olish uchun index.html ichida inline kichik skript ham bor —
 * Vue mount bo'lgunigacha to'g'ri klass o'rnatiladi.
 */

export type Theme = 'light' | 'dark' | 'system'
export type EffectiveTheme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'lms.theme'

export function getStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'system'
  const v = window.localStorage.getItem(THEME_STORAGE_KEY)
  return v === 'light' || v === 'dark' || v === 'system' ? v : 'system'
}

export function getSystemTheme(): EffectiveTheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function getEffectiveTheme(theme: Theme): EffectiveTheme {
  return theme === 'system' ? getSystemTheme() : theme
}

export function applyTheme(theme: Theme): EffectiveTheme {
  const effective = getEffectiveTheme(theme)
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', effective === 'dark')
  }
  return effective
}

export function persistTheme(theme: Theme): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(THEME_STORAGE_KEY, theme)
}
