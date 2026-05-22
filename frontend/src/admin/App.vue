<script setup lang="ts">
import { RouterView } from 'vue-router'
import UiConfirmHost from '@shared/components/ui/UiConfirmHost.vue'
import UiToastHost from '@shared/components/ui/UiToastHost.vue'
</script>

<template>
  <RouterView />
  <UiConfirmHost />
  <UiToastHost />
</template>
