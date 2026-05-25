<script setup lang="ts">
/**
 * Topbar — Phase 17 (professional).
 *
 * Burger tugmasi:
 *   - Desktop (>=lg): sidebar collapse/expand toggle
 *   - Mobile (<lg):   mobile drawer toggle
 *
 * Tarkibi: burger | search (md+) | actions slot | user-menu slot.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useSidebar } from '@shared/composables/useSidebar'

interface Props {
  searchPlaceholder?: string
  userName?: string
  userRole?: string
  initials?: string
  avatarColor?: 'foreground' | 'info' | 'destructive' | 'success'
  showSearch?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  searchPlaceholder: '',
  userName: '',
  userRole: '',
  initials: '?',
  avatarColor: 'foreground',
  showSearch: true,
})

const emit = defineEmits<{
  search: [value: string]
  toggleMobile: []
}>()

const { t } = useI18n()
const { toggleCollapsed, toggleMobile } = useSidebar()

function onBurgerClick() {
  // Mobile'da drawer ochiladi, desktop'da sidebar collapse/expand
  if (window.matchMedia('(min-width: 1024px)').matches) {
    toggleCollapsed()
  } else {
    toggleMobile()
    emit('toggleMobile')
  }
}

const avatarStyle = computed(() => {
  switch (props.avatarColor) {
    case 'info':
      return 'background: var(--info, #2563eb); color: white;'
    case 'destructive':
      return 'background: var(--destructive, #dc2626); color: white;'
    case 'success':
      return 'background: var(--success, #16a34a); color: white;'
    default:
      return ''
  }
})
</script>

<template>
  <header
    class="bg-background border-b border-border px-4 lg:px-6 h-[60px] flex items-center gap-3 lg:gap-4 sticky top-0 z-30"
  >
    <!-- Burger — har doim ko'rinadi (desktop: collapse, mobile: drawer) -->
    <button
      type="button"
      class="w-10 h-10 -ml-1 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors shrink-0"
      :aria-label="t('a11y.open_menu')"
      :title="t('a11y.open_menu')"
      @click="onBurgerClick"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <path d="M3 6h18M3 12h18M3 18h18" />
      </svg>
    </button>

    <!-- Search (md+) -->
    <div v-if="showSearch" class="hidden md:block flex-1 max-w-[400px] relative">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <circle cx="6" cy="6" r="4" />
        <path d="m9 9 3 3" />
      </svg>
      <input
        :placeholder="searchPlaceholder"
        class="w-full bg-muted border border-transparent rounded-md py-2 pl-9 pr-3 text-[13px] outline-none focus:border-border-strong focus:bg-background transition"
        @input="$emit('search', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <div v-else class="flex-1" />
    <div v-if="showSearch" class="md:hidden flex-1" />

    <!-- Actions (notifications, theme, locale) — ml-auto bilan o'ng tomonga -->
    <div class="ml-auto flex items-center gap-1.5">
      <slot name="actions" />

      <slot name="toggles" />

      <!-- Separator -->
      <div
        v-if="$slots['user-menu'] || userName"
        class="hidden md:block w-px h-6 bg-border mx-1"
        aria-hidden="true"
      />

      <!-- User pill slot -->
      <slot name="user-menu">
        <div v-if="userName" class="flex items-center gap-2.5 px-2 py-1">
          <div
            class="w-8 h-8 rounded-full bg-foreground text-background grid place-items-center text-[12px] font-semibold"
            :style="avatarStyle"
          >
            {{ initials }}
          </div>
          <div class="hidden md:block text-[12px] leading-tight">
            <div class="font-medium">{{ userName }}</div>
            <div
              v-if="userRole"
              class="font-mono text-[10px] text-muted-foreground uppercase tracking-wider"
            >
              {{ userRole }}
            </div>
          </div>
        </div>
      </slot>
    </div>
  </header>
</template>
