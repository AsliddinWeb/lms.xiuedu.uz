<script setup lang="ts">
/**
 * Wireframe `.breadcrumb` — Geist Mono UPPERCASE 11px, mute.
 *
 * Items quyidagilarning birortasi bo'lishi mumkin:
 *  - oddiy string (matn, bosilmaydi)
 *  - object: { label, to } — `to` bo'lsa RouterLink sifatida bosilishi mumkin
 *
 * Eng oxirgi item HAR DOIM aktiv (foreground, bosilmaydi) — wireframe pattern.
 */
import { RouterLink, type RouteLocationRaw } from 'vue-router'

export interface BreadcrumbItem {
  label: string
  to?: RouteLocationRaw
}

interface Props {
  items?: Array<string | BreadcrumbItem>
}
defineProps<Props>()

function getLabel(item: string | BreadcrumbItem): string {
  return typeof item === 'string' ? item : item.label
}
function getTo(item: string | BreadcrumbItem): RouteLocationRaw | null {
  return typeof item === 'string' ? null : item.to ?? null
}
</script>

<template>
  <div class="breadcrumb">
    <template v-if="items && items.length > 0">
      <template v-for="(item, i) in items" :key="i">
        <span v-if="i > 0" class="breadcrumb-sep" aria-hidden="true">·</span>
        <!-- Eng oxirgi item — aktiv, bosilmaydi -->
        <span
          v-if="i === items.length - 1"
          class="breadcrumb-current"
        >{{ getLabel(item) }}</span>
        <!-- Boshqa itemlar — agar `to` mavjud bo'lsa link, aks holda oddiy matn -->
        <RouterLink
          v-else-if="getTo(item)"
          :to="getTo(item) as RouteLocationRaw"
          class="breadcrumb-link"
        >{{ getLabel(item) }}</RouterLink>
        <span v-else class="breadcrumb-muted">{{ getLabel(item) }}</span>
      </template>
    </template>
    <slot v-else />
  </div>
</template>

<style scoped>
.breadcrumb-sep {
  opacity: 0.5;
}
.breadcrumb-link {
  color: inherit;
  text-decoration: none;
  transition: color 100ms;
}
.breadcrumb-link:hover {
  color: var(--fg);
  text-decoration: underline;
}
.breadcrumb-current {
  color: var(--fg);
}
</style>
