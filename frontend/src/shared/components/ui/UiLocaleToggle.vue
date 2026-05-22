<script setup lang="ts">
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { useI18n } from 'vue-i18n'

import { type Locale, SUPPORTED_LOCALES } from '@shared/i18n'
import { useLocaleStore } from '@shared/stores/locale'

interface Props {
  /** auth-aside ichida ishlatish uchun (oq fonda qora dropdown emas, oq matn) */
  inverse?: boolean
}
withDefaults(defineProps<Props>(), { inverse: false })

const store = useLocaleStore()
const { t } = useI18n()

const labels: Record<Locale, string> = {
  'uz-lat': "O'zbek (lotin)",
  'uz-cyr': 'Ўзбек (кирилл)',
  ru: 'Русский',
  en: 'English',
}

const shortLabels: Record<Locale, string> = {
  'uz-lat': 'UZ',
  'uz-cyr': 'УЗ',
  ru: 'RU',
  en: 'EN',
}
</script>

<template>
  <Menu as="div" class="relative">
    <MenuButton
      class="flex items-center gap-1.5 px-2 h-9 rounded-md border border-transparent transition-colors hover:bg-muted hover:border-border"
      :class="
        inverse
          ? 'text-white/70 hover:text-white hover:bg-white/10 hover:border-white/20'
          : 'text-muted-foreground hover:text-foreground'
      "
      :title="t('locale.title')"
      :aria-label="t('locale.title')"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      <span class="font-mono text-[11px] font-medium tabular-nums">
        {{ shortLabels[store.locale] }}
      </span>
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
        class="absolute right-0 mt-1.5 w-48 origin-top-right rounded-md border border-border bg-background shadow-lg z-50 focus:outline-none overflow-hidden"
      >
        <div class="px-3 py-2 mono-tag border-b border-border">{{ t('locale.title') }}</div>
        <div class="p-1 flex flex-col gap-0.5">
          <MenuItem v-for="loc in SUPPORTED_LOCALES" :key="loc" v-slot="{ active }" as="template">
            <button
              type="button"
              @click="store.setLocale(loc)"
              :class="[
                'w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-left transition-colors',
                active ? 'bg-muted' : '',
                store.locale === loc
                  ? 'text-foreground font-medium'
                  : 'text-muted-foreground',
              ]"
            >
              <span
                class="font-mono text-[10px] bg-muted text-muted-foreground rounded px-1.5 py-0.5"
              >
                {{ shortLabels[loc] }}
              </span>
              <span class="flex-1">{{ labels[loc] }}</span>
              <svg
                v-if="store.locale === loc"
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
