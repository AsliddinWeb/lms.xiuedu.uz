<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { authApi } from '@shared/api/auth'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

// ---------- 2FA setup ----------

type SetupState = 'idle' | 'pending' | 'showing_qr' | 'enabled'
const setupState = ref<SetupState>('idle')
const setupQr = ref<string | null>(null)
const setupSecret = ref<string | null>(null)
const setupCode = ref('')
const backupCodes = ref<string[]>([])
const setupError = ref<string | null>(null)
const codesCopied = ref(false)

async function copyBackupCodes() {
  try {
    await navigator.clipboard.writeText(backupCodes.value.join('\n'))
    codesCopied.value = true
    setTimeout(() => {
      codesCopied.value = false
    }, 2000)
  } catch {
    // Clipboard API ishlamasa — silent
  }
}

async function startSetup() {
  setupError.value = null
  setupState.value = 'pending'
  try {
    const res = await authApi.setup2FA()
    setupSecret.value = res.secret
    setupQr.value = `data:image/png;base64,${res.qr_png_base64}`
    setupState.value = 'showing_qr'
  } catch (e) {
    setupState.value = 'idle'
    setupError.value = extractErrorMessage(e, t('security.setup_failed'))
  }
}

async function confirmEnable() {
  setupError.value = null
  try {
    const res = await authApi.enable2FA(setupCode.value)
    backupCodes.value = res.backup_codes
    setupState.value = 'enabled'
    setupCode.value = ''
    await auth.fetchMe()
  } catch (e) {
    setupError.value = extractErrorMessage(e, t('security.code_wrong'))
  }
}

// ---------- 2FA disable ----------

const disableOpen = ref(false)
const disablePassword = ref('')
const disableCode = ref('')
const disableError = ref<string | null>(null)
const disableLoading = ref(false)

async function handleDisable() {
  disableError.value = null
  disableLoading.value = true
  try {
    await authApi.disable2FA(disablePassword.value, disableCode.value)
    await auth.fetchMe()
    disableOpen.value = false
    disablePassword.value = ''
    disableCode.value = ''
  } catch (e) {
    disableError.value = extractErrorMessage(e, t('common.delete_error'))
  } finally {
    disableLoading.value = false
  }
}

// ---------- Change password ----------

const oldPass = ref('')
const newPass = ref('')
const newPassConfirm = ref('')
const passError = ref<string | null>(null)
const passSuccess = ref(false)
const passLoading = ref(false)

async function handleChangePassword() {
  passError.value = null
  passSuccess.value = false
  if (newPass.value !== newPassConfirm.value) {
    passError.value = t('security.password_mismatch')
    return
  }
  passLoading.value = true
  try {
    await authApi.changePassword(oldPass.value, newPass.value)
    passSuccess.value = true
    oldPass.value = ''
    newPass.value = ''
    newPassConfirm.value = ''
  } catch (e) {
    passError.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    passLoading.value = false
  }
}

// ---------- Email resend ----------

const resendDone = ref(false)
const resendError = ref<string | null>(null)
async function resendVerification() {
  resendError.value = null
  try {
    await authApi.resendVerification()
    resendDone.value = true
  } catch (e) {
    resendError.value = extractErrorMessage(e, t('common.save_error'))
  }
}
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('profile.title'), t('security.title')]"
    class="mb-6"
  />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('security.title') }}</h1>
    <p class="page-subtitle">{{ t('security.subtitle') }}</p>
  </div>

  <div class="space-y-4">
    <!-- Email verified status -->
    <UiCard :title="t('security.email_section')">
      <template #actions>
        <UiBadge :variant="auth.user?.is_verified ? 'success' : 'warning'" with-dot>
          {{ auth.user?.is_verified ? t('profile.verified') : t('profile.unverified') }}
        </UiBadge>
      </template>
      <p class="font-mono text-[12px] text-muted-foreground mb-3">{{ auth.user?.email }}</p>
      <UiAlert v-if="resendDone" variant="success" class="mb-3">
        {{ t('security.resend_sent') }}
      </UiAlert>
      <UiAlert v-if="resendError" variant="danger" class="mb-3">{{ resendError }}</UiAlert>
      <UiButton
        v-if="!auth.user?.is_verified"
        variant="outline"
        size="sm"
        @click="resendVerification"
      >
        {{ t('security.resend_btn') }}
      </UiButton>
    </UiCard>

    <!-- 2FA setup -->
    <UiCard :title="t('security.twofa_section')">
      <template #actions>
        <UiBadge :variant="auth.user?.is_2fa_enabled ? 'success' : 'default'" with-dot>
          {{ auth.user?.is_2fa_enabled ? t('dashboard.twofa_on') : t('dashboard.twofa_off') }}
        </UiBadge>
      </template>

      <UiAlert v-if="setupError" variant="danger" class="mb-3">{{ setupError }}</UiAlert>

      <!-- 2FA o'chirilgan holat -->
      <div v-if="!auth.user?.is_2fa_enabled && setupState === 'idle'">
        <p class="text-[13px] text-muted-foreground mb-3">
          {{ t('security.twofa_intro') }}
        </p>
        <UiButton @click="startSetup">{{ t('security.twofa_enable') }}</UiButton>
      </div>

      <!-- QR ko'rsatish + kodni kiritish -->
      <div v-else-if="setupState === 'showing_qr'">
        <p class="text-[13px] mb-3">1. {{ t('security.qr_step1') }}</p>
        <div class="bg-white p-3 rounded-md inline-block mb-3 border border-border">
          <img v-if="setupQr" :src="setupQr" alt="2FA QR" width="180" height="180" />
        </div>
        <p class="text-[12px] text-muted-foreground mb-3">
          {{ t('security.qr_fallback') }}
          <code class="font-mono bg-muted text-foreground px-1.5 py-0.5 rounded ml-1">{{
            setupSecret
          }}</code>
        </p>
        <p class="text-[13px] mb-3">2. {{ t('security.qr_step2') }}</p>
        <UiFormField label="" required>
          <UiInput v-model="setupCode" type="text" placeholder="123456" autocomplete="one-time-code" />
        </UiFormField>
        <div class="flex gap-2">
          <UiButton @click="confirmEnable">{{ t('security.confirm_enable') }}</UiButton>
          <UiButton variant="ghost" @click="setupState = 'idle'">{{ t('common.cancel') }}</UiButton>
        </div>
      </div>

      <!-- Backup codes ko'rsatish -->
      <div v-else-if="setupState === 'enabled'">
        <UiAlert variant="success" class="mb-3">
          {{ t('security.backup_codes_intro') }}
        </UiAlert>
        <div class="grid grid-cols-2 gap-2 mb-3 font-mono text-[13px]">
          <div
            v-for="c in backupCodes"
            :key="c"
            class="border border-border rounded px-3 py-2 bg-muted text-center"
          >
            {{ c }}
          </div>
        </div>
        <div class="flex gap-2">
          <UiButton variant="outline" size="sm" @click="copyBackupCodes">
            {{ codesCopied ? t('security.copied') : t('security.copy_backup_codes') }}
          </UiButton>
          <UiButton variant="ghost" size="sm" @click="setupState = 'idle'">
            {{ t('common.close') }}
          </UiButton>
        </div>
      </div>

      <!-- 2FA yoqilgan holat -->
      <div v-else-if="auth.user?.is_2fa_enabled">
        <p class="text-[13px] text-muted-foreground mb-3">
          {{ t('security.twofa_protected') }}
        </p>
        <UiButton variant="danger" size="sm" @click="disableOpen = !disableOpen">
          {{ disableOpen ? t('common.cancel') : t('security.twofa_disable') }}
        </UiButton>

        <div v-if="disableOpen" class="mt-4 pt-4 border-t border-border">
          <UiAlert v-if="disableError" variant="danger" class="mb-3">{{ disableError }}</UiAlert>
          <UiFormField :label="t('security.current_password')" required>
            <UiInput v-model="disablePassword" type="password" required />
          </UiFormField>
          <UiFormField :label="t('security.twofa_or_backup')" required>
            <UiInput v-model="disableCode" type="text" required placeholder="123456" />
          </UiFormField>
          <UiButton variant="danger" :loading="disableLoading" @click="handleDisable">
            {{ t('security.confirm_disable') }}
          </UiButton>
        </div>
      </div>
    </UiCard>

    <!-- Change password -->
    <UiCard :title="t('security.password_section')">
      <UiAlert v-if="passError" variant="danger" class="mb-3">{{ passError }}</UiAlert>
      <UiAlert v-if="passSuccess" variant="success" class="mb-3">
        {{ t('security.password_changed') }}
      </UiAlert>

      <form @submit.prevent="handleChangePassword">
        <UiFormField :label="t('security.current_password')" required>
          <UiInput v-model="oldPass" type="password" autocomplete="current-password" required />
        </UiFormField>
        <UiFormField
          :label="t('security.new_password')"
          :hint="t('security.new_password_hint')"
          required
        >
          <UiInput v-model="newPass" type="password" autocomplete="new-password" required />
        </UiFormField>
        <UiFormField :label="t('security.new_password_confirm')" required>
          <UiInput v-model="newPassConfirm" type="password" autocomplete="new-password" required />
        </UiFormField>
        <UiButton type="submit" :loading="passLoading">{{ t('security.change_btn') }}</UiButton>
      </form>
    </UiCard>
  </div>
</template>
