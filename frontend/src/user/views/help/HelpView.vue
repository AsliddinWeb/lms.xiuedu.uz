<script setup lang="ts">
/**
 * Yordam markazi — tez havolalar, ko'p so'raladigan savollar (FAQ), aloqa.
 */
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiNavIcon from '@shared/components/ui/UiNavIcon.vue'

const { t } = useI18n()

const SUPPORT_EMAIL = 'support@xiuedu.uz'

const quickLinks = [
  { to: '/app/learning', icon: 'courses', label: 'nav.my_learning' },
  { to: '/app/assignments', icon: 'assignments', label: 'nav.assignments' },
  { to: '/app/exams', icon: 'exams', label: 'nav.exams' },
  { to: '/app/schedule', icon: 'schedule', label: 'nav.schedule' },
  { to: '/app/certificates', icon: 'certificates', label: 'nav.certificates' },
  { to: '/app/achievements', icon: 'achievements', label: 'nav.achievements' },
]

const faqKeys = ['enroll', 'certificate', 'exam', 'live', 'badge', 'password']
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('help.title')]"
    class="mb-4"
  />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('help.title') }}</h1>
    <p class="page-subtitle">{{ t('help.subtitle') }}</p>
  </div>

  <!-- Tez havolalar -->
  <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
    {{ t('help.quick_links') }}
  </h2>
  <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-8">
    <RouterLink
      v-for="link in quickLinks"
      :key="link.to"
      :to="link.to"
      class="group"
    >
      <UiCard
        class="p-4 flex items-center gap-3 transition-colors hover:border-foreground/30"
      >
        <span
          class="w-10 h-10 rounded-md grid place-items-center shrink-0 bg-muted text-foreground/80 group-hover:bg-foreground group-hover:text-background transition-colors"
        >
          <UiNavIcon :name="link.icon" />
        </span>
        <span class="text-[13px] font-medium">{{ t(link.label) }}</span>
      </UiCard>
    </RouterLink>
  </div>

  <!-- FAQ -->
  <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
    {{ t('help.faq') }}
  </h2>
  <div class="space-y-2 mb-8">
    <UiCard
      v-for="key in faqKeys"
      :key="key"
      no-padding
      class="overflow-hidden"
    >
      <details class="group">
        <summary
          class="flex items-center justify-between gap-3 px-4 py-3 cursor-pointer list-none select-none hover:bg-muted/40 transition-colors"
        >
          <span class="text-[13px] font-medium">{{ t(`help.q_${key}`) }}</span>
          <svg
            class="w-4 h-4 text-muted-foreground shrink-0 transition-transform group-open:rotate-180"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </summary>
        <div class="px-4 pb-4 pt-3 border-t border-border/60">
          <p class="text-[13px] text-muted-foreground leading-relaxed">
            {{ t(`help.a_${key}`) }}
          </p>
        </div>
      </details>
    </UiCard>
  </div>

  <!-- Aloqa -->
  <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
    {{ t('help.contact') }}
  </h2>
  <UiCard class="p-5">
    <div class="flex items-start gap-4">
      <span
        class="w-12 h-12 rounded-full grid place-items-center shrink-0 text-[#1f3a5f] bg-gradient-to-br from-[#f3e6c4] to-[#d3a945] ring-1 ring-[#c19a3e]/50"
      >
        <UiNavIcon name="help" />
      </span>
      <div class="flex-1 min-w-0">
        <p class="text-[13px] text-muted-foreground mb-2 leading-relaxed">
          {{ t('help.contact_desc') }}
        </p>
        <a
          :href="`mailto:${SUPPORT_EMAIL}`"
          class="inline-flex items-center gap-2 text-[13px] font-medium text-foreground hover:underline"
        >
          <svg
            class="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
          </svg>
          {{ SUPPORT_EMAIL }}
        </a>
      </div>
    </div>
  </UiCard>
</template>
