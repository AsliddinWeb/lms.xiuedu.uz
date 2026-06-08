<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiButton from '@shared/components/ui/UiButton.vue'
import UiDrawer from '@shared/components/ui/UiDrawer.vue'
import UiFormField from '@shared/components/ui/UiFormField.vue'
import UiInput from '@shared/components/ui/UiInput.vue'
import { extractErrorMessage } from '@shared/api/client'
import { usersApi } from '@shared/api/users'
import type { UserDetail } from '@shared/types/users'

import { useUsersStore } from '@admin/stores/users'

interface Props {
  open: boolean
  user?: UserDetail | null
}

const props = withDefaults(defineProps<Props>(), { user: null })

const emit = defineEmits<{
  close: []
  saved: []
}>()

const { t } = useI18n()
const store = useUsersStore()

const isEdit = computed(() => !!props.user)
const title = computed(() =>
  isEdit.value ? t('admin_users.drawer_edit_title') : t('admin_users.drawer_create_title'),
)

const fullName = ref('')
const email = ref('')
const phone = ref('')
const password = ref('')
const isActive = ref(true)
const isVerified = ref(false)
const selectedRoles = ref<Set<string>>(new Set())

const errorMsg = ref<string | null>(null)
const submitting = ref(false)

watch(
  () => [props.open, props.user],
  () => {
    errorMsg.value = null
    if (props.open) {
      void store.fetchRoles()
      if (props.user) {
        fullName.value = props.user.full_name
        email.value = props.user.email
        phone.value = props.user.phone ?? ''
        password.value = ''
        isActive.value = props.user.is_active
        isVerified.value = props.user.is_verified
        selectedRoles.value = new Set(props.user.roles)
      } else {
        fullName.value = ''
        email.value = ''
        phone.value = ''
        password.value = ''
        isActive.value = true
        isVerified.value = false
        selectedRoles.value = new Set()
      }
    }
  },
  { immediate: true },
)

function toggleRole(code: string) {
  const next = new Set(selectedRoles.value)
  if (next.has(code)) next.delete(code)
  else next.add(code)
  selectedRoles.value = next
}

async function handleSubmit() {
  errorMsg.value = null
  submitting.value = true
  try {
    if (isEdit.value && props.user) {
      // Update qayta yangilanganda parolni alohida endpoint orqali qayta o'rnatish
      await store.update(props.user.id, {
        full_name: fullName.value,
        phone: phone.value || null,
        is_active: isActive.value,
        is_verified: isVerified.value,
      })
      if (password.value) {
        await usersApi.setPassword(props.user.id, password.value)
      }
      // Rollar farq qilsa — almashtirish
      const newRoles = Array.from(selectedRoles.value).sort()
      const oldRoles = [...props.user.roles].sort()
      if (JSON.stringify(newRoles) !== JSON.stringify(oldRoles)) {
        await store.replaceRoles(props.user.id, newRoles)
      }
    } else {
      await store.create({
        email: email.value,
        password: password.value,
        full_name: fullName.value,
        phone: phone.value || undefined,
        is_active: isActive.value,
        is_verified: isVerified.value,
        role_codes: Array.from(selectedRoles.value),
      })
    }
    emit('saved')
    emit('close')
  } catch (e) {
    errorMsg.value = extractErrorMessage(e, t('admin_users.save_error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UiDrawer :open="open" :title="title" width="md" @close="emit('close')">
    <UiAlert v-if="errorMsg" variant="danger" class="mb-4">{{ errorMsg }}</UiAlert>

    <form id="user-form" @submit.prevent="handleSubmit" class="space-y-1">
      <UiFormField :label="t('admin_users.f_full_name')" required>
        <UiInput v-model="fullName" required :placeholder="t('admin_users.f_full_name_ph')" />
      </UiFormField>

      <UiFormField :label="t('admin_users.f_email')" required>
        <UiInput
          v-model="email"
          type="email"
          required
          :disabled="isEdit"
          :placeholder="t('admin_users.f_email_ph')"
        />
      </UiFormField>

      <UiFormField :label="t('admin_users.f_phone')">
        <UiInput v-model="phone" type="tel" :placeholder="t('admin_users.f_phone_ph')" />
      </UiFormField>

      <UiFormField
        :label="isEdit ? t('admin_users.f_password_new') : t('admin_users.f_password')"
        :required="!isEdit"
        :hint="t('admin_users.f_password_hint')"
      >
        <UiInput
          v-model="password"
          type="password"
          :required="!isEdit"
          :placeholder="t('admin_users.f_password_ph')"
        />
      </UiFormField>

      <div class="grid grid-cols-2 gap-3 mb-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="isActive" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
          <span class="text-[13px]">{{ t('admin_users.f_active') }}</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="isVerified" type="checkbox" class="w-3.5 h-3.5 accent-foreground" />
          <span class="text-[13px]">{{ t('admin_users.f_verified') }}</span>
        </label>
      </div>

      <div class="mb-4">
        <div class="text-xs font-medium text-foreground mb-2">{{ t('admin_users.f_roles') }}</div>
        <div class="grid grid-cols-2 gap-2">
          <label
            v-for="r in store.roles"
            :key="r.code"
            class="flex items-center gap-2 px-2.5 py-1.5 border border-border rounded-md text-[13px] cursor-pointer hover:bg-muted"
          >
            <input
              type="checkbox"
              :checked="selectedRoles.has(r.code)"
              @change="toggleRole(r.code)"
              class="w-3.5 h-3.5 accent-foreground"
            />
            <span class="truncate">{{ r.name }}</span>
          </label>
        </div>
      </div>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <UiButton variant="outline" :disabled="submitting" @click="emit('close')">
          {{ t('admin_users.drawer_cancel') }}
        </UiButton>
        <UiButton type="submit" :loading="submitting" form="user-form">
          {{ isEdit ? t('admin_users.save') : t('admin_users.create') }}
        </UiButton>
      </div>
    </template>
  </UiDrawer>
</template>
