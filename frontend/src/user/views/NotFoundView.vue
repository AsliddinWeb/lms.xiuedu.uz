<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center text-center bg-[var(--wireframe-bg)]">
    <div>
      <div class="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-3">
        {{ t('common.not_found_title') }}
      </div>
      <h1 class="font-serif text-5xl mb-4">{{ t('common.not_found_subtitle') }}</h1>
      <RouterLink
        to="/"
        class="inline-flex items-center gap-1.5 text-[13px] text-foreground font-medium hover:underline"
      >
        ← {{ t('common.go_home') }}
      </RouterLink>
    </div>
  </div>
</template>
