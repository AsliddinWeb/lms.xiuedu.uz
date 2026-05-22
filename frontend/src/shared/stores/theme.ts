import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  applyTheme,
  getEffectiveTheme,
  getStoredTheme,
  persistTheme,
  type EffectiveTheme,
  type Theme,
} from '@shared/utils/theme'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(getStoredTheme())
  const effectiveTheme = ref<EffectiveTheme>(getEffectiveTheme(theme.value))

  // Boshlang'ich klassni qo'llash (FOUC skript allaqachon ishlagan, lekin idempotent)
  applyTheme(theme.value)

  // System preference o'zgarsa, "system" rejimda app ham yangilansin
  if (typeof window !== 'undefined' && window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      if (theme.value === 'system') {
        effectiveTheme.value = applyTheme('system')
      }
    }
    if (mq.addEventListener) mq.addEventListener('change', onChange)
    else mq.addListener(onChange) // legacy
  }

  function setTheme(t: Theme): void {
    theme.value = t
    persistTheme(t)
    effectiveTheme.value = applyTheme(t)
  }

  function toggle(): void {
    setTheme(effectiveTheme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, effectiveTheme, setTheme, toggle }
})
