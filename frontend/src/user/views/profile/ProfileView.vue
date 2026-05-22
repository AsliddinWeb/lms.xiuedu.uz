<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiAvatarUpload from '@shared/components/ui/UiAvatarUpload.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import { authApi } from '@shared/api/auth'
import { extractErrorMessage } from '@shared/api/client'
import { confirm } from '@shared/composables/useConfirm'
import { toast } from '@shared/composables/useToast'
import { useAuthStore } from '@shared/stores/auth'
import { useLocaleStore } from '@shared/stores/locale'
import { SUPPORTED_LOCALES, type Locale } from '@shared/i18n'

const { t } = useI18n()
const auth = useAuthStore()
const localeStore = useLocaleStore()

// Form state
const fullName = ref('')
const phone = ref('')
const pinfl = ref('')
const passportSeries = ref('')
const passportNumber = ref('')
const birthdate = ref('')
const gender = ref<string | null>(null)
const nationality = ref('')
const address = ref('')
const bio = ref('')
const language = ref<string>('uz-lat')
const timezone = ref<string>('Asia/Tashkent')

// Notification preferences
const notifEmail = ref(true)
const notifSms = ref(false)
const notifTelegram = ref(false)
const notifBrowser = ref(true)

const initialLoading = ref(true)
const submitting = ref(false)
const avatarLoading = ref(false)
const errorMsg = ref<string | null>(null)
const successMsg = ref<string | null>(null)

const genderOptions = computed(() => [
  { value: 'male', label: t('profile.gender_male') },
  { value: 'female', label: t('profile.gender_female') },
])
const langOptions = computed(() => [
  { value: 'uz-lat', label: t('profile.lang_uz_lat') },
  { value: 'uz-cyr', label: t('profile.lang_uz_cyr') },
  { value: 'ru', label: t('profile.lang_ru') },
  { value: 'en', label: t('profile.lang_en') },
])
const timezoneOptions = computed(() => [
  { value: 'Asia/Tashkent', label: t('profile.tz_tashkent') },
  { value: 'Asia/Samarkand', label: t('profile.tz_samarkand') },
  { value: 'Europe/Moscow', label: t('profile.tz_moscow') },
  { value: 'Asia/Almaty', label: t('profile.tz_almaty') },
  { value: 'UTC', label: 'UTC' },
])

const initials = computed(() => {
  const n = auth.user?.full_name ?? ''
  return n
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('') || '?'
})

const isHemisAccount = computed(() => !!auth.user?.hemis_id)

async function load() {
  initialLoading.value = true
  errorMsg.value = null
  try {
    const me = await authApi.getMe()
    fullName.value = me.full_name
    phone.value = me.phone ?? ''
    if (me.profile) {
      pinfl.value = me.profile.pinfl ?? ''
      passportSeries.value = me.profile.passport_series ?? ''
      passportNumber.value = me.profile.passport_number ?? ''
      birthdate.value = me.profile.birthdate ?? ''
      gender.value = me.profile.gender
      nationality.value = me.profile.nationality ?? ''
      address.value = me.profile.address ?? ''
      bio.value = me.profile.bio ?? ''
      language.value = me.profile.language || 'uz-lat'
      timezone.value = me.profile.timezone || 'Asia/Tashkent'
      const np = me.profile.notification_preferences || {}
      notifEmail.value = np.email !== false
      notifSms.value = !!np.sms
      notifTelegram.value = !!np.telegram
      notifBrowser.value = np.browser !== false
    }
    auth.user = me
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    initialLoading.value = false
  }
}

async function handleSave() {
  errorMsg.value = null
  successMsg.value = null
  submitting.value = true
  try {
    const me = await authApi.updateMe({
      full_name: fullName.value.trim(),
      phone: phone.value.trim() || null,
      pinfl: pinfl.value.trim() || null,
      passport_series: passportSeries.value.trim() || null,
      passport_number: passportNumber.value.trim() || null,
      birthdate: birthdate.value || null,
      gender: gender.value,
      nationality: nationality.value.trim() || null,
      address: address.value.trim() || null,
      bio: bio.value.trim() || null,
      language: language.value,
      timezone: timezone.value,
    })
    auth.user = me
    successMsg.value = t('profile.saved')
    // Profile language → lokal locale ham yangilanadi
    if (SUPPORTED_LOCALES.includes(language.value as Locale)) {
      localeStore.setLocale(language.value as Locale)
    }
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    submitting.value = false
  }
}

async function handlePreferences() {
  errorMsg.value = null
  try {
    const me = await authApi.updatePreferences({
      email: notifEmail.value,
      sms: notifSms.value,
      telegram: notifTelegram.value,
      browser: notifBrowser.value,
    })
    auth.user = me
    successMsg.value = t('profile.prefs_saved')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  }
}

async function handleAvatarUpload(file: File) {
  errorMsg.value = null
  avatarLoading.value = true
  try {
    const res = await authApi.uploadAvatar(file)
    if (auth.user) auth.user = { ...auth.user, avatar_url: res.avatar_url }
    successMsg.value = t('profile.avatar_uploaded')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    avatarLoading.value = false
  }
}

async function handleAvatarRemove() {
  errorMsg.value = null
  const ok = await confirm({
    title: t('profile.avatar_confirm_remove'),
    variant: 'danger',
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!ok) return
  avatarLoading.value = true
  try {
    await authApi.deleteAvatar()
    if (auth.user) auth.user = { ...auth.user, avatar_url: null }
    toast.success(t('common.deleted'))
  } catch (e) {
    const msg = extractErrorMessage(e, t('common.delete_error'))
    errorMsg.value = msg
    toast.error(msg)
  } finally {
    avatarLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('profile.title')]"
    class="mb-6"
  />

  <div class="mb-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="page-title mb-1.5">{{ t('profile.title') }}</h1>
        <p class="page-subtitle">{{ t('profile.subtitle') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiBadge :variant="auth.user?.is_verified ? 'success' : 'warning'" with-dot>
          {{ auth.user?.is_verified ? t('profile.verified') : t('profile.unverified') }}
        </UiBadge>
        <UiBadge v-if="isHemisAccount" variant="info" with-dot>
          {{ t('profile.hemis_account') }}
        </UiBadge>
      </div>
    </div>
  </div>

  <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>
  <UiAlert v-if="successMsg" variant="success" class="mb-4">{{ successMsg }}</UiAlert>

  <div v-if="initialLoading" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <div v-else class="space-y-4">
    <!-- Avatar -->
    <UiCard :title="t('profile.card_avatar')">
      <UiAvatarUpload
        :model-value="auth.user?.avatar_url ?? null"
        :initials="initials"
        :loading="avatarLoading"
        @upload="handleAvatarUpload"
        @remove="handleAvatarRemove"
      />
    </UiCard>

    <!-- Asosiy ma'lumotlar -->
    <UiCard :title="t('profile.card_main')">
      <UiAlert v-if="isHemisAccount" variant="info" class="mb-4">
        {{ t('profile.hemis_warn') }}
      </UiAlert>

      <form @submit.prevent="handleSave">
        <UiFormField :label="t('profile.field_full_name')" required>
          <UiInput v-model="fullName" required :disabled="isHemisAccount" />
        </UiFormField>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <UiFormField :label="t('profile.field_email_locked')">
            <UiInput :model-value="auth.user?.email ?? ''" disabled />
          </UiFormField>
          <UiFormField :label="t('profile.field_phone')">
            <UiInput v-model="phone" type="tel" :placeholder="t('profile.placeholder_phone')" />
          </UiFormField>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <UiFormField :label="t('profile.field_pinfl')">
            <UiInput v-model="pinfl" :disabled="isHemisAccount" />
          </UiFormField>
          <UiFormField :label="t('profile.field_passport_series')">
            <UiInput v-model="passportSeries" :placeholder="t('profile.placeholder_passport_series')" />
          </UiFormField>
          <UiFormField :label="t('profile.field_passport_number')">
            <UiInput v-model="passportNumber" :placeholder="t('profile.placeholder_passport_number')" />
          </UiFormField>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <UiFormField :label="t('profile.field_birthdate')" :hint="t('profile.field_birthdate_hint')">
            <UiInput v-model="birthdate" :placeholder="t('profile.placeholder_birthdate')" />
          </UiFormField>
          <UiFormField :label="t('profile.field_gender')">
            <UiSelect
              v-model="gender"
              :options="genderOptions"
              :placeholder="t('profile.gender_unselected')"
            />
          </UiFormField>
          <UiFormField :label="t('profile.field_nationality')">
            <UiInput v-model="nationality" :placeholder="t('profile.placeholder_nationality')" />
          </UiFormField>
        </div>

        <UiFormField :label="t('profile.field_address')">
          <UiInput v-model="address" :placeholder="t('profile.placeholder_address')" />
        </UiFormField>

        <UiFormField :label="t('profile.field_bio')">
          <textarea
            v-model="bio"
            rows="3"
            class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
            :placeholder="t('profile.placeholder_bio')"
          ></textarea>
        </UiFormField>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <UiFormField :label="t('profile.field_language')">
            <UiSelect v-model="language" :options="langOptions" />
          </UiFormField>
          <UiFormField :label="t('profile.field_timezone')">
            <UiSelect v-model="timezone" :options="timezoneOptions" />
          </UiFormField>
        </div>

        <UiButton type="submit" :loading="submitting">{{ t('common.save') }}</UiButton>
      </form>
    </UiCard>

    <!-- Bildirishnomalar -->
    <UiCard :title="t('profile.card_notifications')">
      <p class="text-[13px] text-muted-foreground mb-4">{{ t('profile.notif_subtitle') }}</p>
      <div class="space-y-2">
        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="notifEmail" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
          <div>
            <div class="text-[13px] font-medium">{{ t('profile.notif_email') }}</div>
            <div class="text-[11px] text-muted-foreground">{{ auth.user?.email }}</div>
          </div>
        </label>
        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="notifSms" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
          <div>
            <div class="text-[13px] font-medium">{{ t('profile.notif_sms') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ phone || t('profile.notif_no_phone') }}
            </div>
          </div>
        </label>
        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="notifTelegram" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
          <div>
            <div class="text-[13px] font-medium">{{ t('profile.notif_telegram') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ t('profile.notif_telegram_hint') }}
            </div>
          </div>
        </label>
        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="notifBrowser" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
          <div>
            <div class="text-[13px] font-medium">{{ t('profile.notif_browser') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ t('profile.notif_browser_hint') }}
            </div>
          </div>
        </label>
      </div>
      <UiButton class="mt-4" @click="handlePreferences">{{ t('common.save') }}</UiButton>
    </UiCard>
  </div>
</template>
