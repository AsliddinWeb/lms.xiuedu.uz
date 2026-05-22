<script setup lang="ts">
/**
 * Wireframe `.sidebar` — 260px width, full-height sticky, 24px+16px padding.
 *
 * Sections — har biri `title` (mono-tag) + `items[]` (icon+label+to+badge).
 * `footerItems` — alohida border-top bilan pastda.
 * `logo` slot — top brand.
 * `footer` slot — eng pastki bo'lim (logout, user info).
 *
 * Phase 8d — mobile responsive: lg breakpoint'gacha (≥1024px) yashirin,
 * `mobileOpen` true bo'lganda overlay drawer sifatida slide in qiladi.
 * Mobile'da menu item bosilganda avtomatik yopiladi.
 */
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterLink, useRoute, type RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'

export interface SidebarNavItem {
  name: string
  icon: string
  label: string
  to?: string  // RouterLink target, agar yo'q bo'lsa disabled
  badge?: string | number
  disabled?: boolean
}

export interface SidebarSection {
  title: string
  items: SidebarNavItem[]
}

interface Props {
  sections: SidebarSection[]
  footerSection?: SidebarSection
  logoText: string
  logoIcon?: string  // 1–3 character mono initials, e.g. "L"
  logoTo?: RouteLocationRaw  // RouterLink target (string yoki { name } object)
  /** Mobile drawer holatda overlay ko'rsatish (kichik ekranlarda). */
  mobileOpen?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  footerSection: undefined,
  logoIcon: 'L',
  logoTo: '/',
  mobileOpen: false,
})

const emit = defineEmits<{ closeMobile: [] }>()
const { t } = useI18n()
const route = useRoute()

// Route o'zgarganda mobile drawer'ni yopish
watch(() => route.fullPath, () => {
  if (props.mobileOpen) emit('closeMobile')
})

// Esc bilan yopish (mobile drawer ochiq bo'lsa)
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.mobileOpen) emit('closeMobile')
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <!-- Mobile overlay (faqat mobileOpen true bo'lganda ko'rinadi) -->
  <Transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="mobileOpen"
      class="fixed inset-0 bg-foreground/40 z-40 lg:hidden"
      aria-hidden="true"
      @click="emit('closeMobile')"
    />
  </Transition>

  <!-- Sidebar (lg dan boshlab static, undan past: fixed drawer) -->
  <aside
    :class="[
      'bg-background border-r border-border px-4 py-6 flex flex-col w-[260px]',
      // Desktop (lg+): static sticky
      'lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto lg:translate-x-0',
      // Mobile (<lg): off-canvas drawer
      'fixed inset-y-0 left-0 z-50 h-screen overflow-y-auto transform transition-transform duration-200 ease-out',
      mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
    :aria-hidden="!mobileOpen && undefined"
  >
    <!-- Logo + close button (faqat mobile'da) -->
    <div class="flex items-center justify-between mb-8">
      <RouterLink
        :to="logoTo"
        class="flex items-center gap-2.5 px-2 font-bold text-base tracking-tight no-underline"
      >
        <div
          class="w-7 h-7 rounded-md bg-foreground text-background grid place-items-center font-mono text-[13px] font-bold"
        >{{ logoIcon }}</div>
        <span class="text-foreground">{{ logoText }}</span>
      </RouterLink>
      <button
        type="button"
        class="lg:hidden p-2 -mr-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
        :aria-label="t('a11y.close')"
        @click="emit('closeMobile')"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Main sections -->
    <div v-for="section in sections" :key="section.title" class="mb-6">
      <div class="sidebar-section-title">{{ section.title }}</div>
      <template v-for="item in section.items" :key="item.name">
        <RouterLink
          v-if="!item.disabled && item.to"
          :to="item.to"
          class="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium text-foreground hover:bg-muted transition-colors no-underline"
          active-class="!bg-foreground !text-background hover:!bg-foreground"
        >
          <UiNavIcon :name="item.icon" />
          <span class="flex-1">{{ item.label }}</span>
          <span
            v-if="item.badge !== undefined"
            class="font-mono text-[11px] bg-muted text-muted-foreground rounded px-1.5 py-0.5 router-link-active-badge"
          >{{ item.badge }}</span>
        </RouterLink>
        <div
          v-else
          class="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium text-muted-foreground cursor-not-allowed"
        >
          <UiNavIcon :name="item.icon" />
          <span class="flex-1">{{ item.label }}</span>
          <span
            v-if="item.badge !== undefined"
            class="font-mono text-[11px] bg-muted text-muted-foreground rounded px-1.5 py-0.5"
          >{{ item.badge }}</span>
        </div>
      </template>
    </div>

    <!-- Footer section (Yordam, Sozlamalar) with border-top -->
    <div
      v-if="footerSection"
      class="mt-auto pt-4 border-t border-border"
    >
      <div v-if="footerSection.title" class="sidebar-section-title">{{ footerSection.title }}</div>
      <template v-for="item in footerSection.items" :key="item.name">
        <RouterLink
          v-if="!item.disabled && item.to"
          :to="item.to"
          class="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium text-foreground hover:bg-muted transition-colors no-underline"
          active-class="!bg-foreground !text-background hover:!bg-foreground"
        >
          <UiNavIcon :name="item.icon" />
          <span class="flex-1">{{ item.label }}</span>
        </RouterLink>
        <div
          v-else
          class="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium text-muted-foreground cursor-not-allowed"
        >
          <UiNavIcon :name="item.icon" />
          <span class="flex-1">{{ item.label }}</span>
        </div>
      </template>
    </div>

    <!-- Free-form footer slot (logout, user info) -->
    <div v-if="$slots.footer" :class="footerSection ? '' : 'mt-auto pt-4 border-t border-border'">
      <slot name="footer" />
    </div>
  </aside>
</template>

<style scoped>
/* Active state'da badge'ning rang inversiyasi (qora bg / oq matn → inverse badge) */
.router-link-active.\!bg-foreground .router-link-active-badge,
a.router-link-exact-active .router-link-active-badge {
  background: rgba(255, 255, 255, 0.15);
  color: var(--bg);
}
</style>
