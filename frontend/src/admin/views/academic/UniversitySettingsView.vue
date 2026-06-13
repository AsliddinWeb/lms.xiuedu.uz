<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { extractErrorMessage } from '@shared/api/client'
import { orgsApi } from '@shared/api/academic'
import type { Organization } from '@shared/types/academic'

const { t } = useI18n()

const xiu = ref<Organization | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const successMsg = ref<string | null>(null)

// Editable fields (lokal state)
const name = ref('')
const shortName = ref('')
const phone = ref('')
const email = ref('')
const website = ref('')
const domain = ref('')
const address = ref('')
const logoUrl = ref('')
const hemisBaseUrl = ref('')

async function load() {
  loading.value = true
  error.value = null
  try {
    const list = await orgsApi.list('XIU')
    const found = list.find((o) => o.code === 'XIU') ?? list[0]
    if (!found) {
      error.value = t('university.not_found')
      return
    }
    xiu.value = found
    name.value = found.name
    shortName.value = found.short_name ?? ''
    phone.value = found.phone ?? ''
    email.value = found.email ?? ''
    website.value = found.website ?? ''
    domain.value = found.domain ?? ''
    address.value = found.address ?? ''
    logoUrl.value = found.logo_url ?? ''
    const settings = (found.settings ?? {}) as { hemis?: { base_url?: string } }
    hemisBaseUrl.value = settings.hemis?.base_url ?? ''
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!xiu.value) return
  saving.value = true
  error.value = null
  successMsg.value = null
  try {
    const newSettings: Record<string, unknown> = { ...(xiu.value.settings ?? {}) }
    if (hemisBaseUrl.value.trim()) {
      newSettings.hemis = { base_url: hemisBaseUrl.value.trim() }
    } else {
      delete newSettings.hemis
    }
    xiu.value = await orgsApi.update(xiu.value.id, {
      name: name.value.trim(),
      short_name: shortName.value.trim() || null,
      phone: phone.value.trim() || null,
      email: email.value.trim() || null,
      website: website.value.trim() || null,
      domain: domain.value.trim() || null,
      address: address.value.trim() || null,
      logo_url: logoUrl.value.trim() || null,
      settings: newSettings,
    })
    successMsg.value = t('university.saved') + ' ✓'
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.save_error'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-6">
    <div>
      <UiBreadcrumb :items="['Admin', t('admin_nav.management'), t('university.title')]" class="mb-6" />
      <h1 class="page-title mb-1.5">{{ t('university.title') }}</h1>
      <p class="page-subtitle">{{ t('university.subtitle') }}</p>
    </div>
    <UiBadge v-if="xiu?.is_active" variant="success" with-dot>
      {{ t('common.active') }}
    </UiBadge>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>
  <UiAlert v-if="successMsg" variant="success" class="mb-4">{{ successMsg }}</UiAlert>

  <div v-if="loading && !xiu" class="text-center py-12 text-muted-foreground">
    {{ t('common.loading') }}
  </div>

  <div v-else-if="xiu" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <!-- Asosiy ma'lumotlar -->
    <UiCard class="lg:col-span-2">
      <template #header>
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('university.section_basic') }}
        </div>
      </template>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('university.field_code')">
          <UiInput :model-value="xiu.code" disabled />
        </UiFormField>
        <UiFormField :label="t('university.field_name')" required>
          <UiInput v-model="name" />
        </UiFormField>
      </div>

      <UiFormField :label="t('university.field_short_name')">
        <UiInput v-model="shortName" />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('university.field_phone')">
          <UiInput v-model="phone" type="tel" placeholder="+998 ..." />
        </UiFormField>
        <UiFormField :label="t('university.field_email')">
          <UiInput v-model="email" type="email" />
        </UiFormField>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <UiFormField :label="t('university.field_website')">
          <UiInput v-model="website" type="url" />
        </UiFormField>
        <UiFormField :label="t('university.field_domain')">
          <UiInput v-model="domain" placeholder="xiuedu.uz" />
        </UiFormField>
      </div>

      <UiFormField :label="t('university.field_address')">
        <textarea
          v-model="address"
          rows="2"
          class="block w-full rounded-md border border-border-strong bg-background text-foreground text-[13px] px-3 py-2 outline-none focus:border-foreground focus:shadow-focus"
        ></textarea>
      </UiFormField>

      <UiFormField :label="t('university.field_logo_url')">
        <UiInput v-model="logoUrl" type="url" />
      </UiFormField>
    </UiCard>

    <!-- HEMIS sozlamalari -->
    <UiCard>
      <template #header>
        <div class="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {{ t('university.section_hemis') }}
        </div>
      </template>

      <p class="text-[12px] text-muted-foreground mb-3">
        {{ t('university.hemis_description') }}
      </p>

      <UiFormField :label="t('university.field_hemis_base_url')">
        <UiInput
          v-model="hemisBaseUrl"
          type="url"
          placeholder="https://student.xiuedu.uz/rest"
        />
        <div class="text-[11px] text-muted-foreground mt-1">
          {{ t('university.hemis_hint') }}
        </div>
      </UiFormField>
    </UiCard>
  </div>

  <div v-if="xiu" class="mt-4 flex justify-end">
    <UiButton
      v-permission="'org.manage'"
      :loading="saving"
      @click="save"
    >
      {{ t('common.save') }}
    </UiButton>
  </div>
</template>
