<script setup lang="ts">
/**
 * Admin auth layout — thin wrapper.
 * AdminLoginView o'zini UiAuthLayout bilan o'rab oladi (split layout).
 */
import { RouterView } from 'vue-router'

import UiLocaleToggle from '@shared/components/ui/UiLocaleToggle.vue'
import UiThemeToggle from '@shared/components/ui/UiThemeToggle.vue'
</script>

<template>
  <div class="min-h-screen bg-background relative">
    <div class="absolute top-4 right-4 z-50 flex items-center gap-1">
      <UiLocaleToggle />
      <UiThemeToggle />
    </div>

    <RouterView />
  </div>
</template>
