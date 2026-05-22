<script setup lang="ts">
/**
 * Topbar'dagi user pill (avatar + ism + role) + dropdown menyu.
 *
 * Pattern:
 *   - Bosilganda dropdown ochiladi: user info bo'limi + nav itemlar (profile, security, ...) + logout
 *   - Profile va Security sidebar'dan olib tashlandi — wireframe 04/12 ga ko'ra ular shu joydan ochilishi kerak
 *   - Headless UI Menu (locale toggle bilan bir xil pattern)
 */
import { computed } from 'vue'
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { RouterLink } from 'vue-router'

import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'

export interface UserMenuItem {
  name: string
  icon: string
  label: string
  to?: string  // RouterLink target
  danger?: boolean  // qizil styled (logout, delete account uchun)
  divider?: boolean  // boshidan oldin border-top
}

interface Props {
  userName: string
  userRole?: string
  initials?: string
  userEmail?: string
  items: UserMenuItem[]
  /** Avatar bg rangi — Topbar bilan bir xil prop. */
  avatarColor?: 'foreground' | 'info' | 'destructive' | 'success'
}

const props = withDefaults(defineProps<Props>(), {
  userRole: '',
  initials: '?',
  userEmail: '',
  avatarColor: 'foreground',
})

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

defineEmits<{ select: [item: UserMenuItem] }>()
</script>

<template>
  <Menu as="div" class="relative">
    <MenuButton
      class="flex items-center gap-2.5 px-2 py-1 rounded-md border border-transparent transition-colors hover:bg-muted hover:border-border"
      :aria-label="userName"
    >
      <div
        class="w-8 h-8 rounded-full bg-foreground text-background grid place-items-center text-[12px] font-semibold"
        :style="avatarStyle"
      >{{ initials }}</div>
      <!-- Phase 8d — ism+role faqat md+ ekranlarda ko'rinadi -->
      <div class="hidden md:block text-[12px] leading-tight text-left">
        <div class="font-medium text-foreground">{{ userName }}</div>
        <div
          v-if="userRole"
          class="font-mono text-[10px] text-muted-foreground uppercase tracking-wider"
        >{{ userRole }}</div>
      </div>
      <svg
        class="hidden md:block text-muted-foreground ml-0.5"
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M3 4.5 6 7.5l3-3" />
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
        class="absolute right-0 mt-1.5 w-64 origin-top-right rounded-md border border-border bg-background shadow-lg z-50 focus:outline-none overflow-hidden"
      >
        <!-- User info header -->
        <div class="px-4 py-3 border-b border-border bg-muted/30">
          <div class="text-[13px] font-semibold text-foreground truncate">
            {{ userName }}
          </div>
          <div
            v-if="userEmail"
            class="font-mono text-[11px] text-muted-foreground truncate mt-0.5"
          >{{ userEmail }}</div>
          <div
            v-if="userRole"
            class="font-mono text-[10px] text-muted-foreground uppercase tracking-wider mt-1"
          >{{ userRole }}</div>
        </div>

        <!-- Items -->
        <div class="p-1 flex flex-col gap-0.5">
          <template v-for="(item, idx) in items" :key="item.name">
            <!-- Divider (faqat ajratuvchi chiziq, MenuItem render qilmaydi) -->
            <div
              v-if="item.divider"
              class="border-t border-border my-1"
              :class="{ 'mt-0': idx === 0 }"
              aria-hidden="true"
            />
            <!-- Oddiy menu item -->
            <MenuItem v-else v-slot="{ active }" as="template">
              <RouterLink
                v-if="item.to"
                :to="item.to"
                :class="[
                  'w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-left transition-colors no-underline',
                  active ? 'bg-muted' : '',
                  item.danger ? 'text-danger-600' : 'text-foreground',
                ]"
                @click="$emit('select', item)"
              >
                <UiNavIcon :name="item.icon" />
                <span class="flex-1">{{ item.label }}</span>
              </RouterLink>
              <button
                v-else
                type="button"
                :class="[
                  'w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-[13px] text-left transition-colors',
                  active ? 'bg-muted' : '',
                  item.danger ? 'text-danger-600' : 'text-foreground',
                ]"
                @click="$emit('select', item)"
              >
                <UiNavIcon :name="item.icon" />
                <span class="flex-1">{{ item.label }}</span>
              </button>
            </MenuItem>
          </template>
        </div>
      </MenuItems>
    </transition>
  </Menu>
</template>
