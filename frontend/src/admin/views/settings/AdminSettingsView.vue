<script setup lang="ts">
/**
 * Admin — Platforma sozlamalari. org.settings.platform (JSONB) ichida saqlanadi.
 * Mavjud kalitlar (masalan hemis) saqlanib qoladi — faqat `platform` yangilanadi.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import UiSelect from '@shared/components/ui/UiSelect.vue'
import UiSettingToggle from '@shared/components/ui/UiSettingToggle.vue'
import { orgsApi } from '@shared/api/academic'
import { extractErrorMessage } from '@shared/api/client'
import { toast } from '@shared/composables/useToast'
import type { Organization } from '@shared/types/academic'

const { t } = useI18n()

const org = ref<Organization | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

// Platforma sozlamalari (org.settings.platform)
const defaultLanguage = ref('uz-lat')
const allowSelf = ref(false)
const defaultEnrollment = ref('manual')
const passingPercent = ref<number>(60)
const featureLive = ref(true)
const featureForum = ref(true)
const featureCertificates = ref(true)
const featureGamification = ref(true)
const emailNotifications = ref(true)

const languageOptions = computedLangOptions()
function computedLangOptions() {
  return [
    { value: 'uz-lat', label: 'O\'zbek (lotin)' },
    { value: 'uz-cyr', label: 'O\'zbek (kirill)' },
    { value: 'ru', label: 'Русский' },
    { value: 'en', label: 'English' },
  ]
}
const enrollmentOptions = [
  { value: 'manual', label: t('courses.enrollment_manual') },
  { value: 'self', label: t('courses.enrollment_self') },
  { value: 'auto', label: t('courses.enrollment_auto') },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    const list = await orgsApi.list('XIU')
    const found = list.find((o) => o.code === 'XIU') ?? list[0]
    if (!found) {
      error.value = t('admin_settings.not_found')
      return
    }
    org.value = found
    const p = ((found.settings ?? {}) as { platform?: Record<string, unknown> }).platform ?? {}
    defaultLanguage.value = (p.default_language as string) ?? 'uz-lat'
    allowSelf.value = Boolean(p.allow_self_registration)
    defaultEnrollment.value = (p.default_enrollment_method as string) ?? 'manual'
    passingPercent.value = typeof p.passing_percent === 'number' ? p.passing_percent : 60
    featureLive.value = p.feature_live !== false
    featureForum.value = p.feature_forum !== false
    featureCertificates.value = p.feature_certificates !== false
    featureGamification.value = p.feature_gamification !== false
    emailNotifications.value = p.email_notifications !== false
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!org.value) return
  saving.value = true
  error.value = null
  try {
    const newSettings: Record<string, unknown> = { ...(org.value.settings ?? {}) }
    newSettings.platform = {
      default_language: defaultLanguage.value,
      allow_self_registration: allowSelf.value,
      default_enrollment_method: defaultEnrollment.value,
      passing_percent: Number(passingPercent.value),
      feature_live: featureLive.value,
      feature_forum: featureForum.value,
      feature_certificates: featureCertificates.value,
      feature_gamification: featureGamification.value,
      email_notifications: emailNotifications.value,
    }
    org.value = await orgsApi.update(org.value.id, { settings: newSettings })
    toast.success(t('admin_settings.saved'))
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <UiBreadcrumb :items="['Admin', t('admin_nav.ops'), t('admin_settings.title')]" class="mb-6" />
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <h1 class="page-title mb-1.5">{{ t('admin_settings.title') }}</h1>
      <p class="page-subtitle">{{ t('admin_settings.subtitle') }}</p>
    </div>
    <UiButton v-permission="'org.manage'" :loading="saving" @click="save">
      {{ t('common.save') }}
    </UiButton>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading && !org" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <div v-else-if="org" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Umumiy -->
    <UiCard :title="t('admin_settings.sec_general')">
      <UiFormField :label="t('admin_settings.f_default_language')" :hint="t('admin_settings.f_default_language_hint')">
        <UiSelect v-model="defaultLanguage" :options="languageOptions" />
      </UiFormField>
    </UiCard>

    <!-- Ro'yxatdan o'tish -->
    <UiCard :title="t('admin_settings.sec_registration')">
      <div class="flex items-center justify-between gap-4 py-1">
        <div>
          <div class="text-[13px] font-medium">{{ t('admin_settings.f_allow_self') }}</div>
          <div class="text-[11px] text-muted-foreground">{{ t('admin_settings.f_allow_self_hint') }}</div>
        </div>
        <UiSettingToggle v-model="allowSelf" />
      </div>
      <UiFormField :label="t('admin_settings.f_default_enrollment')" class="mt-3">
        <UiSelect v-model="defaultEnrollment" :options="enrollmentOptions" />
      </UiFormField>
    </UiCard>

    <!-- Baholash -->
    <UiCard :title="t('admin_settings.sec_grading')">
      <UiFormField :label="t('admin_settings.f_passing_percent')" :hint="t('admin_settings.f_passing_hint')">
        <UiInput v-model="passingPercent" type="number" min="0" max="100" />
      </UiFormField>
    </UiCard>

    <!-- Integratsiya -->
    <UiCard :title="t('admin_settings.sec_integration')">
      <div class="flex items-center justify-between gap-4 py-1">
        <div>
          <div class="text-[13px] font-medium">{{ t('admin_settings.f_email_notifications') }}</div>
          <div class="text-[11px] text-muted-foreground">{{ t('admin_settings.f_email_hint') }}</div>
        </div>
        <UiSettingToggle v-model="emailNotifications" />
      </div>
    </UiCard>

    <!-- Modullar -->
    <UiCard :title="t('admin_settings.sec_features')" class="lg:col-span-2">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
        <div class="flex items-center justify-between gap-4">
          <span class="text-[13px]">{{ t('admin_settings.f_feature_live') }}</span>
          <UiSettingToggle v-model="featureLive" />
        </div>
        <div class="flex items-center justify-between gap-4">
          <span class="text-[13px]">{{ t('admin_settings.f_feature_forum') }}</span>
          <UiSettingToggle v-model="featureForum" />
        </div>
        <div class="flex items-center justify-between gap-4">
          <span class="text-[13px]">{{ t('admin_settings.f_feature_certificates') }}</span>
          <UiSettingToggle v-model="featureCertificates" />
        </div>
        <div class="flex items-center justify-between gap-4">
          <span class="text-[13px]">{{ t('admin_settings.f_feature_gamification') }}</span>
          <UiSettingToggle v-model="featureGamification" />
        </div>
      </div>
    </UiCard>
  </div>
</template>
