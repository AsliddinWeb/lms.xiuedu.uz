<script setup lang="ts">
/**
 * Sozlamalar — ko'rinish (tema/til/yon panel), bildirishnoma kanallari,
 * hisob havolalari. Mavjud store/endpoint'lardan foydalanadi.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'
import { authApi } from '@shared/api/auth'
import { extractErrorMessage } from '@shared/api/client'
import { SUPPORTED_LOCALES, type Locale } from '@shared/i18n'
import { useSidebar } from '@shared/composables/useSidebar'
import { useLocaleStore } from '@shared/stores/locale'
import { useThemeStore } from '@shared/stores/theme'
import type { Theme } from '@shared/utils/theme'
import SettingToggle from '@shared/components/ui/UiSettingToggle.vue'

const { t } = useI18n()
const themeStore = useThemeStore()
const localeStore = useLocaleStore()
const { collapsed, toggleCollapsed } = useSidebar()

const themeOptions: { value: Theme; label: string }[] = [
  { value: 'light', label: 'theme.light' },
  { value: 'dark', label: 'theme.dark' },
  { value: 'system', label: 'theme.system' },
]

function setTheme(v: Theme) {
  themeStore.setTheme(v)
}

function setLocale(v: Locale) {
  localeStore.setLocale(v)
  // serverga ham saqlash (best-effort — email/bildirishnoma tili uchun)
  authApi.updateMe({ language: v }).catch(() => {})
}

// --- Bildirishnoma kanallari ---
type NotifKey = 'email' | 'sms' | 'telegram' | 'browser'
const notif = ref<Record<NotifKey, boolean>>({
  email: true,
  sms: false,
  telegram: false,
  browser: false,
})
const notifKeys: NotifKey[] = ['email', 'sms', 'telegram', 'browser']
const loading = ref(true)
const error = ref<string | null>(null)
const savedFlash = ref(false)
let savedTimer: ReturnType<typeof setTimeout> | null = null

async function loadPrefs() {
  loading.value = true
  error.value = null
  try {
    const me = await authApi.getMe()
    const prefs = (me.profile?.notification_preferences ?? {}) as Record<
      string,
      boolean
    >
    notif.value = {
      email: prefs.email ?? true,
      sms: prefs.sms ?? false,
      telegram: prefs.telegram ?? false,
      browser: prefs.browser ?? false,
    }
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function onNotifChange(key: NotifKey, value: boolean) {
  notif.value[key] = value
  try {
    await authApi.updatePreferences({ ...notif.value })
    savedFlash.value = true
    if (savedTimer) clearTimeout(savedTimer)
    savedTimer = setTimeout(() => (savedFlash.value = false), 2000)
  } catch (e) {
    notif.value[key] = !value // qaytar
    error.value = extractErrorMessage(e, t('common.save_error'))
  }
}

onMounted(loadPrefs)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('settings.title')]"
    class="mb-4"
  />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('settings.title') }}</h1>
    <p class="page-subtitle">{{ t('settings.subtitle') }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Ko'rinish -->
    <UiCard :title="t('settings.appearance')">
      <div class="space-y-5">
        <!-- Tema -->
        <div>
          <div class="text-[13px] font-medium mb-2">{{ t('theme.title') }}</div>
          <div class="flex gap-2">
            <button
              v-for="opt in themeOptions"
              :key="opt.value"
              type="button"
              class="flex-1 px-3 py-2 rounded-md text-[12px] font-medium border transition-colors"
              :class="
                themeStore.theme === opt.value
                  ? 'bg-foreground text-background border-foreground'
                  : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/30'
              "
              @click="setTheme(opt.value)"
            >
              {{ t(opt.label) }}
            </button>
          </div>
        </div>

        <!-- Til -->
        <div>
          <div class="text-[13px] font-medium mb-2">{{ t('locale.title') }}</div>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="loc in SUPPORTED_LOCALES"
              :key="loc"
              type="button"
              class="px-3 py-2 rounded-md text-[12px] font-medium border transition-colors text-left"
              :class="
                localeStore.locale === loc
                  ? 'bg-foreground text-background border-foreground'
                  : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/30'
              "
              @click="setLocale(loc)"
            >
              {{ t(`locale.${loc}`) }}
            </button>
          </div>
        </div>

        <!-- Yon panel -->
        <div class="flex items-center justify-between gap-4 pt-1">
          <div class="min-w-0">
            <div class="text-[13px] font-medium">{{ t('settings.sidebar_label') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ t('settings.sidebar_desc') }}
            </div>
          </div>
          <SettingToggle
            :model-value="collapsed"
            @update:model-value="toggleCollapsed"
          />
        </div>
      </div>
    </UiCard>

    <!-- Bildirishnomalar -->
    <UiCard :title="t('profile.card_notifications')">
      <p class="text-[13px] text-muted-foreground mb-4">
        {{ t('profile.notif_subtitle') }}
        <span
          v-if="savedFlash"
          class="ml-2 text-[11px] font-mono text-emerald-600 dark:text-emerald-400"
        >
          ✓ {{ t('settings.saved') }}
        </span>
      </p>
      <div v-if="loading" class="text-[13px] text-muted-foreground">…</div>
      <div v-else class="space-y-3">
        <div
          v-for="key in notifKeys"
          :key="key"
          class="flex items-center justify-between gap-4"
        >
          <div class="text-[13px] font-medium">{{ t(`profile.notif_${key}`) }}</div>
          <SettingToggle
            :model-value="notif[key]"
            @update:model-value="(v) => onNotifChange(key, v)"
          />
        </div>
      </div>
    </UiCard>

    <!-- Hisob -->
    <UiCard :title="t('settings.account')" class="lg:col-span-2">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <RouterLink to="/app/profile" class="group">
          <div
            class="p-4 rounded-md border border-border flex items-center gap-3 transition-colors hover:border-foreground/30"
          >
            <span
              class="w-10 h-10 rounded-md grid place-items-center shrink-0 bg-muted text-foreground/80 group-hover:bg-foreground group-hover:text-background transition-colors"
            >
              <UiNavIcon name="profile" />
            </span>
            <div class="min-w-0">
              <div class="text-[13px] font-medium">{{ t('settings.account_profile') }}</div>
              <div class="text-[11px] text-muted-foreground">
                {{ t('settings.account_profile_desc') }}
              </div>
            </div>
          </div>
        </RouterLink>

        <RouterLink to="/app/security" class="group">
          <div
            class="p-4 rounded-md border border-border flex items-center gap-3 transition-colors hover:border-foreground/30"
          >
            <span
              class="w-10 h-10 rounded-md grid place-items-center shrink-0 bg-muted text-foreground/80 group-hover:bg-foreground group-hover:text-background transition-colors"
            >
              <UiNavIcon name="security" />
            </span>
            <div class="min-w-0">
              <div class="text-[13px] font-medium">{{ t('settings.account_security') }}</div>
              <div class="text-[11px] text-muted-foreground">
                {{ t('settings.account_security_desc') }}
              </div>
            </div>
          </div>
        </RouterLink>
      </div>
    </UiCard>
  </div>
</template>
