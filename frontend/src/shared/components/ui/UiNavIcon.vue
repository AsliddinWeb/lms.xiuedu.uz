<script setup lang="ts">
/**
 * Sidebar nav iconlari — wireframe `md_files/ui_wireframes/lms_ui/pages/*.html` dan
 * 1:1 ko'chirilgan. 16×16 viewBox, stroke 1.5, currentColor.
 *
 * Manba: design-system.md §6 — icon SVG path nuqtalari aniq belgilangan.
 */
interface Props {
  name: string
  size?: number
}
withDefaults(defineProps<Props>(), { size: 16 })
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    aria-hidden="true"
    class="shrink-0"
  >
    <!-- DASHBOARD — 4 squares grid -->
    <template v-if="name === 'dashboard'">
      <rect x="2" y="2" width="5" height="5" />
      <rect x="9" y="2" width="5" height="5" />
      <rect x="2" y="9" width="5" height="5" />
      <rect x="9" y="9" width="5" height="5" />
    </template>

    <!-- COURSES (catalog/my-learning/my-courses) — 3-line list -->
    <template v-else-if="['courses', 'catalog', 'my-learning', 'my-courses'].includes(name)">
      <path d="M2 4h12M2 8h12M2 12h8" />
    </template>

    <!-- ASSIGNMENTS / TEACHER-ASSIGNMENTS — clipboard -->
    <template v-else-if="name === 'assignments'">
      <rect x="3" y="2" width="10" height="12" />
      <path d="M5 5h6M5 8h6M5 11h4" />
    </template>

    <!-- SCHEDULE / CALENDARS — clock -->
    <template v-else-if="name === 'schedule'">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 4v4l2 2" />
    </template>

    <!-- CALENDARS — calendar (admin) -->
    <template v-else-if="name === 'calendars'">
      <rect x="2" y="3" width="12" height="10" rx="1" />
      <path d="M2 6h12M5 1v3M11 1v3" />
    </template>

    <!-- GRADES / ANALYTICS / REPORTS — bar chart -->
    <template v-else-if="['grades', 'analytics', 'reports'].includes(name)">
      <path d="M2 14V2M2 14h12M5 11V7M8 11V4M11 11V8" />
    </template>

    <!-- PAYMENTS — credit card -->
    <template v-else-if="name === 'payments'">
      <rect x="2" y="4" width="12" height="9" rx="1" />
      <path d="M2 7h12" />
    </template>

    <!-- CERTIFICATES — frame with inner square -->
    <template v-else-if="name === 'certificates'">
      <path d="M3 3h10v10H3z M6 6h4v4H6z" />
    </template>

    <!-- FORUM — chat lines -->
    <template v-else-if="name === 'forum'">
      <path d="M3 4h10M3 8h10M3 12h6" />
    </template>

    <!-- ACHIEVEMENTS — trophy/cup -->
    <template v-else-if="name === 'achievements'">
      <path d="M5 2h6v3a3 3 0 0 1-6 0V2z" />
      <path d="M5 3H3v2a2 2 0 0 0 2 2M11 3h2v2a2 2 0 0 1-2 2" />
      <path d="M6 8v2h4V8M5 14h6M8 10v4" />
    </template>

    <!-- MESSAGES — envelope -->
    <template v-else-if="name === 'messages'">
      <path d="M2 4l6 5 6-5M2 4v8h12V4" />
    </template>

    <!-- HELP — circle with ! -->
    <template v-else-if="name === 'help'">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3M8 10v.5" />
    </template>

    <!-- SETTINGS — gear (concentric circles) -->
    <template v-else-if="name === 'settings'">
      <circle cx="8" cy="8" r="2" />
      <circle cx="8" cy="8" r="6" />
    </template>

    <!-- LIVE / RECORD — record dot (filled inner circle) -->
    <template v-else-if="name === 'live'">
      <circle cx="8" cy="8" r="6" />
      <circle cx="8" cy="8" r="2" fill="currentColor" />
    </template>

    <!-- USERS — two heads + bodies -->
    <template v-else-if="name === 'users' || name === 'students' || name === 'departments'">
      <circle cx="6" cy="5" r="2" />
      <circle cx="11" cy="5" r="2" />
      <path d="M2 13a4 4 0 0 1 8 0M7 13a4 4 0 0 1 8 0" />
    </template>

    <!-- PROFILE — single user -->
    <template v-else-if="name === 'profile'">
      <circle cx="8" cy="5" r="2.5" />
      <path d="M3 14a5 5 0 0 1 10 0" />
    </template>

    <!-- SECURITY — shield -->
    <template v-else-if="name === 'security'">
      <path d="M8 2 3 4v4c0 3 2.5 5.5 5 6 2.5-.5 5-3 5-6V4l-5-2z" />
      <path d="M6 8l1.5 1.5L10 7" />
    </template>

    <!-- ROLES — key (wireframe-style: circle + bit) -->
    <template v-else-if="name === 'roles'">
      <circle cx="5" cy="11" r="3" />
      <path d="M7 9l6-6M11 5l2 2M9 7l2 2" />
    </template>

    <!-- COURSE-BUILDER — plus -->
    <template v-else-if="name === 'course-builder'">
      <path d="M8 2v12M2 8h12" />
    </template>

    <!-- ORGANIZATIONS / UNIVERSITY — building -->
    <template v-else-if="['organizations', 'university'].includes(name)">
      <path d="M2 14V5l6-3 6 3v9" />
      <path d="M2 14h12" />
      <path d="M6 14v-4h4v4" />
      <path d="M6 7h.01M10 7h.01" />
    </template>

    <!-- FACULTIES — building with windows -->
    <template v-else-if="name === 'faculties'">
      <path d="M2 14V3h8v11" />
      <path d="M10 8h4v6" />
      <path d="M2 14h12" />
      <path d="M4 6h2M4 9h2M8 6h.01M8 9h.01" />
    </template>

    <!-- SPECIALTIES — id card -->
    <template v-else-if="name === 'specialties'">
      <rect x="2" y="3" width="12" height="10" rx="1" />
      <circle cx="6" cy="8" r="1.5" />
      <path d="M9 7h3M9 10h2" />
    </template>

    <!-- SUBJECTS — open book -->
    <template v-else-if="name === 'subjects'">
      <path d="M2 3v10c2 0 4 .5 6 2 2-1.5 4-2 6-2V3" />
      <path d="M2 3c2 0 4 .5 6 2v10" />
      <path d="M14 3c-2 0-4 .5-6 2" />
    </template>

    <!-- CURRICULA — document with lines -->
    <template v-else-if="name === 'curricula'">
      <path d="M10 2H4v12h8V4l-2-2z" />
      <path d="M10 2v2h2" />
      <path d="M6 8h4M6 11h3" />
    </template>

    <!-- CONTENT — folder -->
    <template v-else-if="name === 'content'">
      <path d="M2 5a1 1 0 0 1 1-1h3l1 1h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5z" />
    </template>

    <!-- AUDIT — document with lines (square) -->
    <template v-else-if="name === 'audit'">
      <path d="M3 3h10v10H3z" />
      <path d="M5 6h6M5 9h6M5 11h4" />
    </template>

    <!-- INTEGRATIONS — connection cross -->
    <template v-else-if="name === 'integrations'">
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1v3M8 12v3M1 8h3M12 8h3" />
    </template>

    <!-- LOGOUT — arrow exit -->
    <template v-else-if="name === 'logout'">
      <path d="M9 14H4a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1h5" />
      <path d="M11 11l3-3-3-3M14 8H7" />
    </template>

    <!-- Fallback dot -->
    <template v-else>
      <circle cx="8" cy="8" r="1.5" fill="currentColor" />
    </template>
  </svg>
</template>
