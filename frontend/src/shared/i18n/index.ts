/**
 * vue-i18n instance — har 4 til o'rnatildi.
 *
 * Foydalanish:
 *   <template>{{ $t('common.save') }}</template>
 *   const { t } = useI18n()
 *   t('auth.login_btn')
 *
 * Locale almashtirish:
 *   import { useLocaleStore } from '@shared/stores/locale'
 *   const l = useLocaleStore()
 *   l.setLocale('ru')
 */

import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import ru from './locales/ru.json'
import uzCyr from './locales/uz-cyr.json'
import uzLat from './locales/uz-lat.json'

export type Locale = 'uz-lat' | 'uz-cyr' | 'ru' | 'en'

export const SUPPORTED_LOCALES: Locale[] = ['uz-lat', 'uz-cyr', 'ru', 'en']
export const DEFAULT_LOCALE: Locale = 'uz-lat'

export const LOCALE_STORAGE_KEY = 'lms.locale'

/**
 * Brauzer til kodidan eng yaqin qo'llab-quvvatlanadigan locale'ni qaytaradi.
 * Misol: 'ru-RU' → 'ru', 'en-US' → 'en', 'uz' → 'uz-lat'.
 */
export function pickLocale(navigatorLang: string | undefined): Locale {
  if (!navigatorLang) return DEFAULT_LOCALE
  const lower = navigatorLang.toLowerCase()
  if (lower.startsWith('ru')) return 'ru'
  if (lower.startsWith('en')) return 'en'
  if (lower.startsWith('uz')) return DEFAULT_LOCALE
  return DEFAULT_LOCALE
}

export function getStoredLocale(): Locale {
  if (typeof window === 'undefined') return DEFAULT_LOCALE
  const v = window.localStorage.getItem(LOCALE_STORAGE_KEY) as Locale | null
  if (v && SUPPORTED_LOCALES.includes(v)) return v
  return pickLocale(window.navigator.language)
}

export function persistLocale(locale: Locale): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(LOCALE_STORAGE_KEY, locale)
}

/**
 * App locale'ini Intl/BCP-47 uchun yaroqli kodga aylantiradi.
 * 'uz-lat'/'uz-cyr' — Intl uchun YAROQSIZ; ular 'uz-Latn'/'uz-Cyrl' ga o'giriladi
 * (aks holda Intl.DateTimeFormat RangeError beradi va sana formatlanmaydi).
 */
export function intlLocale(locale: string): string {
  if (locale === 'uz-lat') return 'uz-Latn'
  if (locale === 'uz-cyr') return 'uz-Cyrl'
  return locale
}

export function applyHtmlLang(locale: Locale): void {
  if (typeof document !== 'undefined') {
    // uz-lat va uz-cyr ikkalasi ham 'uz' BCP-47 (lotin/kirill — script subtag)
    document.documentElement.setAttribute('lang', intlLocale(locale))
  }
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: getStoredLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    'uz-lat': uzLat,
    'uz-cyr': uzCyr,
    ru,
    en,
  },
  // HTML inside translations (e.g. brand.tagline_serif) — Vue v-html bilan ishlatamiz
  warnHtmlMessage: false,
})
