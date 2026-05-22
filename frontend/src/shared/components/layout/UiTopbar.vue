<script setup lang="ts">
/**
 * Wireframe `.topbar` — 12px 32px padding, 1px border-bottom, sticky.
 * Tarkibi:
 *   - search 400px max
 *   - actions (gap 8px ml-auto): icon-btn'lar + theme toggle + locale toggle + avatar+role pill
 * Avatar pill: 32x32 avatar + 12px ism + 10px mono role
 *
 * Phase 8d — mobile: hamburger tugma chap tomonda (<lg), search yashirinadi
 * (kichik ekranda bo'sh joy yo'q), avatar pill'da faqat avatar qoladi.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  searchPlaceholder?: string
  userName?: string
  userRole?: string  // pill labelu, e.g. "3-KURS · CS"
  initials?: string  // avatar bosh harflari
  avatarColor?: 'foreground' | 'info' | 'destructive' | 'success'
  showSearch?: boolean
  /** Hamburger tugmasini ko'rsatish (mobile drawer ochish uchun). */
  showMobileToggle?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  searchPlaceholder: '',
  userName: '',
  userRole: '',
  initials: '?',
  avatarColor: 'foreground',
  showSearch: true,
  showMobileToggle: true,
})

const emit = defineEmits<{
  search: [value: string]
  toggleMobile: []
}>()

const { t } = useI18n()

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
    class="bg-background border-b border-border px-4 lg:px-8 py-3 flex items-center gap-3 lg:gap-4 sticky top-0 z-40"
  >
    <!-- Mobile hamburger (faqat <lg) -->
    <button
      v-if="showMobileToggle"
      type="button"
      class="lg:hidden w-10 h-10 -ml-1 grid place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
      :aria-label="t('a11y.open_menu')"
      @click="emit('toggleMobile')"
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        aria-hidden="true"
      >
        <path d="M3 6h18M3 12h18M3 18h18" />
      </svg>
    </button>

    <!-- Search (yashiringan <md ekranlarda) -->
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

    <!-- Actions slot (notifications, messages, etc.) — ml-auto bilan o'ng tomonga itariladi -->
    <div class="ml-auto flex items-center gap-1.5">
      <slot name="actions" />

      <slot name="toggles">
        <!-- default toggles via slot inject — host uchun bo'sh -->
      </slot>

      <!-- Separator before user pill — kichik ekranda yashirin -->
      <div
        v-if="$slots['user-menu'] || userName"
        class="hidden md:block w-px h-6 bg-border mx-1"
        aria-hidden="true"
      />

      <!-- User pill slot — parent UiUserMenu (dropdown) ni shu yerga joylaydi.
           Slot bo'lmasa, oddiy non-clickable pill ko'rsatiladi (backward-compat). -->
      <slot name="user-menu">
        <div v-if="userName" class="flex items-center gap-2.5 px-2 py-1">
          <div
            class="w-8 h-8 rounded-full bg-foreground text-background grid place-items-center text-[12px] font-semibold"
            :style="avatarStyle"
          >{{ initials }}</div>
          <div class="hidden md:block text-[12px] leading-tight">
            <div class="font-medium">{{ userName }}</div>
            <div
              v-if="userRole"
              class="font-mono text-[10px] text-muted-foreground uppercase tracking-wider"
            >{{ userRole }}</div>
          </div>
        </div>
      </slot>
    </div>
  </header>
</template>
