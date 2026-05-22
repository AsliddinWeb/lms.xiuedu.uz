<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Menu,
  MenuButton,
  MenuItem,
  MenuItems,
} from '@headlessui/vue'

import { useThemeStore } from '@shared/stores/theme'
import type { Theme } from '@shared/utils/theme'

const { t } = useI18n()

interface Props {
  /** Joriy ko'rinadigan ikon rangini meros qilib olish (auth-aside ichida ishlatish uchun). */
  inverse?: boolean
}

withDefaults(defineProps<Props>(), { inverse: false })

const theme = useThemeStore()

const options: { value: Theme; label: string; iconPath: string }[] = [
  {
    value: 'light',
    label: 'Kunduzgi',
    // sun
    iconPath:
      'M12 4V2m0 20v-2m8-8h2M2 12h2m13.66-5.66 1.4-1.4M4.94 19.06l1.4-1.4m0-11.32-1.4-1.4m13.42 13.42 1.4 1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  },
  {
    value: 'dark',
    label: 'Tungi',
    // moon
    iconPath: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z',
  },
  {
    value: 'system',
    label: 'Tizim',
    // monitor
    iconPath: 'M3 4h18v12H3zM8 20h8M12 16v4',
  },
]

const currentOption = computed(() => options.find((o) => o.value === theme.theme) ?? options[2])
</script>

<template>
  <Menu as="div" class="relative">
    <MenuButton
      class="grid place-items-center w-9 h-9 rounded-md border border-transparent transition-colors hover:bg-muted hover:border-border"
      :class="inverse ? 'text-white/70 hover:text-white hover:bg-white/10 hover:border-white/20' : 'text-muted-foreground hover:text-foreground'"
      :title="`${t('theme.title')}: ${currentOption.label}`"
      :aria-label="t('theme.title')"
    >
      <svg
        v-if="theme.effectiveTheme === 'dark'"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
      </svg>
      <svg
        v-else
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="4" />
        <path
          d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
        />
      </svg>
    </MenuButton>

    <transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <MenuItems
        class="absolute right-0 mt-1.5 w-44 origin-top-right rounded-md border border-border bg-background shadow-lg z-50 focus:outline-none overflow-hidden"
      >
        <div class="px-3 py-2 mono-tag border-b border-border">Tema</div>
        <div class="p-1 flex flex-col gap-0.5">
          <MenuItem
            v-for="opt in options"
            :key="opt.value"
            v-slot="{ active }"
            as="template"
          >
            <button
              type="button"
              @click="theme.setTheme(opt.value)"
              :class="[
                'w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-left transition-colors',
                active ? 'bg-muted' : '',
                theme.theme === opt.value
                  ? 'text-foreground font-medium'
                  : 'text-muted-foreground',
              ]"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <template v-if="opt.value === 'light'">
                  <circle cx="12" cy="12" r="4" />
                  <path
                    d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
                  />
                </template>
                <template v-else-if="opt.value === 'dark'">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
                </template>
                <template v-else>
                  <rect x="3" y="4" width="18" height="12" rx="1" />
                  <path d="M8 20h8M12 16v4" />
                </template>
              </svg>
              <span class="flex-1">{{ opt.label }}</span>
              <svg
                v-if="theme.theme === opt.value"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="m5 12 5 5L20 7" />
              </svg>
            </button>
          </MenuItem>
        </div>
      </MenuItems>
    </transition>
  </Menu>
</template>
