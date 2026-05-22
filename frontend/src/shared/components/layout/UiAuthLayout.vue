<script setup lang="ts">
/**
 * Wireframe `.auth-page` — 50/50 split (mobile'da chap yashirinadi).
 * - Chap (`.auth-side`): qora `bg-foreground`, brending + KPI/steps + footer mono-tag
 * - O'ng (`.auth-form`): oq forma, max 400px, centered
 *
 * Slot'lar:
 *   #side:  branding (heading + body content) — agar bo'sh, default brand title ko'rsatadi
 *   #side-bottom:  qora panel ostidagi mono-tag (559-son qaror eslatmasi va sh.k.)
 *   default: o'ng tomon form
 *   #form-header:  forma yuqorisidagi mono-tag + h1 + subtitle
 *
 * Props:
 *   brandTitle  — chap tomon LMS logo yonidagi nom
 *   homeTo      — logo bosilganda border (default `/`)
 */
import { RouterLink } from 'vue-router'

interface Props {
  brandTitle?: string
  homeTo?: string
}
withDefaults(defineProps<Props>(), {
  brandTitle: 'XIU EduPlatform',
  homeTo: '/',
})
</script>

<template>
  <div class="min-h-screen grid grid-cols-1 md:grid-cols-2">
    <!-- LEFT SIDE — dark branding -->
    <aside
      class="bg-foreground text-background p-12 flex-col justify-between relative overflow-hidden hidden md:flex"
      style="
        background-image:
          radial-gradient(circle at 30% 20%, rgba(255,255,255,0.05) 0%, transparent 40%),
          radial-gradient(circle at 70% 80%, rgba(255,255,255,0.05) 0%, transparent 40%);
      "
    >
      <div class="relative z-10">
        <!-- Logo -->
        <RouterLink :to="homeTo" class="flex items-center gap-3 mb-12 no-underline text-background">
          <div
            class="w-9 h-9 bg-background text-foreground grid place-items-center font-mono font-bold rounded-lg text-[12px]"
          >LMS</div>
          <span class="font-semibold text-base">{{ brandTitle }}</span>
        </RouterLink>

        <slot name="side">
          <div class="font-serif text-[40px] leading-[1.1] mb-6 max-w-md">
            Bilim olishning yangi <em class="italic">raqamli</em> davri.
          </div>
        </slot>
      </div>

      <!-- Bottom mono-tag (559-qaror, etc.) -->
      <div class="relative z-10 font-mono text-[11px] uppercase tracking-widest opacity-50">
        <slot name="side-bottom">
          O'zR Vazirlar Mahkamasining 559-son qarori asosida
        </slot>
      </div>
    </aside>

    <!-- RIGHT SIDE — form -->
    <main class="flex items-center justify-center p-12 bg-background">
      <div class="w-full max-w-[400px]">
        <slot />
      </div>
    </main>
  </div>
</template>
