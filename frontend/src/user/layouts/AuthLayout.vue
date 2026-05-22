<script setup lang="ts">
/**
 * Auth layout (wireframe 01–03).
 * Bu layout faqat global toggle'lar va RouterView ni o'rab oladi.
 * Har sahifa o'zining `UiAuthLayout` (side content) bilan ichidan dizayn qiladi.
 */
import { RouterView } from 'vue-router'

import UiLocaleToggle from '@shared/components/ui/UiLocaleToggle.vue'
import UiThemeToggle from '@shared/components/ui/UiThemeToggle.vue'
</script>

<template>
  <div class="min-h-screen bg-background relative">
    <!-- Top-right global toggle'lar -->
    <div class="absolute top-4 right-4 z-50 flex items-center gap-1">
      <UiLocaleToggle />
      <UiThemeToggle />
    </div>

    <RouterView />
  </div>
</template>
