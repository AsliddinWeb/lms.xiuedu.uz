<script setup lang="ts">
/**
 * Sidebar — Phase 17 (professional, collapsible).
 *
 * Desktop:
 *   - 260px (expand) yoki 64px (collapse) — smooth width transition
 *   - Collapsed holatda faqat iconlar ko'rinadi (label title tooltip orqali)
 *   - Pastida collapse/expand tugmasi
 *
 * Mobile (<lg):
 *   - Off-canvas drawer (260px), overlay
 *   - Route o'zgarganda yopiladi
 *   - Esc tugmasi yopadi
 *
 * Sections — `title` (mono-tag) + `items[]` (icon+label+to+badge).
 * `footerSection` — alohida border-top.
 */
import { watch } from 'vue'
import { RouterLink, useRoute, type RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'

import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'
import { useSidebar, useSidebarEscClose } from '@shared/composables/useSidebar'

export interface SidebarNavItem {
  name: string
  icon: string
  label: string
  to?: string
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
  logoIcon?: string
  logoTo?: RouteLocationRaw
}

withDefaults(defineProps<Props>(), {
  footerSection: undefined,
  logoIcon: 'L',
  logoTo: '/',
})

const { t } = useI18n()
const route = useRoute()
const { collapsed, mobileOpen, toggleCollapsed, closeMobile } = useSidebar()

// Faqat sidebar mount qilinganda Esc listener qo'shamiz
useSidebarEscClose()

// Route o'zgarganda mobile drawer yopiladi (desktop collapse holati saqlanadi)
watch(() => route.fullPath, () => {
  if (mobileOpen.value) closeMobile()
})
</script>

<template>
  <!-- Mobile overlay -->
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
      @click="closeMobile"
    />
  </Transition>

  <!-- Sidebar -->
  <aside
    :class="[
      'bg-background border-r border-border flex flex-col z-50',
      'transition-[width] duration-200 ease-out',
      // Desktop sticky + collapsible width
      'lg:sticky lg:top-0 lg:h-screen lg:translate-x-0',
      collapsed ? 'lg:w-[64px]' : 'lg:w-[260px]',
      // Mobile drawer
      'fixed inset-y-0 left-0 h-screen w-[260px] overflow-x-hidden',
      'transform transition-transform duration-200 ease-out',
      mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
    :aria-hidden="!mobileOpen && undefined"
  >
    <!-- Header: logo + close btn (mobile) -->
    <div
      :class="[
        'flex items-center border-b border-border h-[60px] shrink-0 px-4',
        collapsed ? 'lg:justify-center lg:px-2' : 'justify-between',
      ]"
    >
      <RouterLink
        :to="logoTo"
        class="flex items-center gap-2.5 font-bold text-base tracking-tight no-underline overflow-hidden"
      >
        <div
          class="w-8 h-8 rounded-md bg-foreground text-background grid place-items-center font-mono text-[13px] font-bold shrink-0"
        >
          {{ logoIcon }}
        </div>
        <span
          v-show="!collapsed"
          class="text-foreground whitespace-nowrap"
        >
          {{ logoText }}
        </span>
      </RouterLink>

      <!-- Mobile close (X) — desktop'da yashirin -->
      <button
        type="button"
        class="lg:hidden p-2 -mr-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
        :aria-label="t('a11y.close')"
        @click="closeMobile"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Scrollable content -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden py-4">
      <!-- Main sections -->
      <div
        v-for="section in sections"
        :key="section.title"
        :class="['mb-6', collapsed ? 'lg:px-2 px-3' : 'px-3']"
      >
        <div
          v-show="!collapsed"
          class="sidebar-section-title px-2.5 mb-2"
        >
          {{ section.title }}
        </div>

        <template v-for="item in section.items" :key="item.name">
          <RouterLink
            v-if="!item.disabled && item.to"
            :to="item.to"
            :title="collapsed ? item.label : undefined"
            :class="[
              'group relative flex items-center rounded-md text-[13px] font-medium text-foreground hover:bg-muted transition-colors no-underline',
              collapsed
                ? 'lg:justify-center lg:px-0 lg:py-3 lg:mb-1 gap-3 px-3 py-2.5'
                : 'gap-3 px-3 py-2.5 mb-0.5',
            ]"
            active-class="!bg-foreground !text-background hover:!bg-foreground"
          >
            <UiNavIcon :name="item.icon" :size="20" />
            <span
              v-show="!collapsed"
              class="flex-1 truncate"
            >
              {{ item.label }}
            </span>
            <span
              v-show="!collapsed && item.badge !== undefined"
              class="font-mono text-[11px] bg-muted text-muted-foreground rounded px-1.5 py-0.5 router-link-active-badge"
            >
              {{ item.badge }}
            </span>
            <!-- Collapsed dot -->
            <span
              v-if="collapsed && item.badge !== undefined"
              class="hidden lg:block absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-foreground router-link-active-dot"
            ></span>
          </RouterLink>

          <div
            v-else
            :title="collapsed ? item.label : undefined"
            :class="[
              'flex items-center rounded-md text-[15px] font-medium text-muted-foreground cursor-not-allowed',
              collapsed
                ? 'lg:justify-center lg:px-0 lg:py-3 lg:mb-1 gap-3 px-3 py-2.5'
                : 'gap-3 px-3 py-2.5 mb-0.5',
            ]"
          >
            <UiNavIcon :name="item.icon" :size="20" />
            <span v-show="!collapsed" class="flex-1 truncate">{{ item.label }}</span>
            <span
              v-show="!collapsed && item.badge !== undefined"
              class="font-mono text-[11px] bg-muted text-muted-foreground rounded px-1.5 py-0.5"
            >
              {{ item.badge }}
            </span>
          </div>
        </template>
      </div>

      <!-- Footer section (Yordam, Sozlamalar) -->
      <div
        v-if="footerSection"
        :class="['mt-4 pt-4 border-t border-border', collapsed ? 'lg:px-2 px-3' : 'px-3']"
      >
        <template v-for="item in footerSection.items" :key="item.name">
          <RouterLink
            v-if="!item.disabled && item.to"
            :to="item.to"
            :title="collapsed ? item.label : undefined"
            :class="[
              'flex items-center rounded-md text-[15px] font-medium text-foreground hover:bg-muted transition-colors no-underline',
              collapsed
                ? 'lg:justify-center lg:px-0 lg:py-3 lg:mb-1 gap-3 px-3 py-2.5'
                : 'gap-3 px-3 py-2.5 mb-0.5',
            ]"
            active-class="!bg-foreground !text-background hover:!bg-foreground"
          >
            <UiNavIcon :name="item.icon" :size="20" />
            <span v-show="!collapsed" class="flex-1 truncate">{{ item.label }}</span>
          </RouterLink>
          <div
            v-else
            :title="collapsed ? item.label : undefined"
            :class="[
              'flex items-center rounded-md text-[15px] font-medium text-muted-foreground cursor-not-allowed',
              collapsed
                ? 'lg:justify-center lg:px-0 lg:py-3 lg:mb-1 gap-3 px-3 py-2.5'
                : 'gap-3 px-3 py-2.5 mb-0.5',
            ]"
          >
            <UiNavIcon :name="item.icon" :size="20" />
            <span v-show="!collapsed" class="flex-1 truncate">{{ item.label }}</span>
          </div>
        </template>
      </div>

      <!-- Free-form footer slot -->
      <div
        v-if="$slots.footer"
        :class="['mt-auto pt-4 border-t border-border', collapsed ? 'lg:px-2 px-3' : 'px-3']"
      >
        <slot name="footer" />
      </div>
    </div>

    <!-- Collapse/expand tugma — desktop only, pastda -->
    <button
      type="button"
      class="hidden lg:flex items-center justify-center h-10 border-t border-border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors shrink-0"
      :aria-label="collapsed ? t('a11y.expand') : t('a11y.collapse')"
      :title="collapsed ? t('a11y.expand') : t('a11y.collapse')"
      @click="toggleCollapsed"
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        :style="{ transform: collapsed ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }"
      >
        <path d="M9 4 5 7l4 3" />
      </svg>
    </button>
  </aside>
</template>

<style scoped>
.sidebar-section-title {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted-fg, #737373);
  font-weight: 600;
}

/* Active'da badge rang inversiyasi */
.router-link-active.\!bg-foreground .router-link-active-badge,
a.router-link-exact-active .router-link-active-badge {
  background: rgba(255, 255, 255, 0.15);
  color: var(--bg, white);
}

.router-link-active.\!bg-foreground .router-link-active-dot {
  background: var(--bg, white);
}
</style>
