import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  applyHtmlLang,
  getStoredLocale,
  i18n,
  persistLocale,
  type Locale,
  SUPPORTED_LOCALES,
} from '@shared/i18n'

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<Locale>(getStoredLocale())

  // Boshlang'ich klassni qo'llash (FOUC skript allaqachon ishlagan)
  applyHtmlLang(locale.value)
  ;(i18n.global.locale as unknown as { value: Locale }).value = locale.value

  function setLocale(next: Locale): void {
    if (!SUPPORTED_LOCALES.includes(next)) return
    locale.value = next
    persistLocale(next)
    applyHtmlLang(next)
    ;(i18n.global.locale as unknown as { value: Locale }).value = next
  }

  return { locale, setLocale }
})
