<script setup lang="ts">
/**
 * Yutuqlar sahifasi — Phase 11e.
 *
 * Tarkibi:
 *   - Yuqorida: jami ball + reyting + nishonlar soni (3 ta stat card)
 *   - Olingan nishonlar + olinmagan katalog
 *   - Leaderboard (scope toggle: umumiy/hafta/oy)
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import UiAlert from '@shared/components/ui/UiAlert.vue'
import UiBadge from '@shared/components/ui/UiBadge.vue'
import UiBreadcrumb from '@shared/components/ui/UiBreadcrumb.vue'
import UiCard from '@shared/components/ui/UiCard.vue'
import UiSkeleton from '@shared/components/ui/UiSkeleton.vue'
import UiStatCard from '@shared/components/ui/UiStatCard.vue'
import {
  gamificationApi,
  type BadgePublic,
  type LeaderboardResponse,
  type MyGamificationStats,
  type UserBadgeItem,
} from '@shared/api/gamification'
import { extractErrorMessage } from '@shared/api/client'
import { useAuthStore } from '@shared/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const stats = ref<MyGamificationStats | null>(null)
const earnedBadges = ref<UserBadgeItem[]>([])
const catalog = ref<BadgePublic[]>([])
const leaderboard = ref<LeaderboardResponse | null>(null)
const scope = ref<'total' | 'weekly' | 'monthly'>('total')
const loading = ref(true)
const error = ref<string | null>(null)

const earnedCodes = computed(
  () => new Set(earnedBadges.value.map((b) => b.badge.code)),
)
const lockedBadges = computed(() =>
  catalog.value.filter((b) => !earnedCodes.value.has(b.code)),
)

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [s, mine, all, lb] = await Promise.all([
      gamificationApi.myStats(),
      gamificationApi.myBadges(),
      gamificationApi.badgeCatalog(),
      gamificationApi.leaderboard(scope.value, 20),
    ])
    stats.value = s
    earnedBadges.value = mine
    catalog.value = all
    leaderboard.value = lb
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  } finally {
    loading.value = false
  }
}

async function reloadLeaderboard() {
  try {
    leaderboard.value = await gamificationApi.leaderboard(scope.value, 20)
  } catch (e) {
    error.value = extractErrorMessage(e, t('common.load_error'))
  }
}

watch(scope, () => {
  void reloadLeaderboard()
})

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString()
}

function catLabel(code: string): string {
  return t(`gamif.category_${code}`)
}

onMounted(loadAll)
</script>

<template>
  <UiBreadcrumb
    :items="[t('dashboard.crumb_home'), t('gamif.title')]"
    class="mb-4"
  />

  <div class="mb-6">
    <h1 class="page-title mb-1.5">{{ t('gamif.title') }}</h1>
    <p class="page-subtitle">{{ t('gamif.subtitle') }}</p>
  </div>

  <UiAlert v-if="error" variant="danger" class="mb-4">{{ error }}</UiAlert>

  <div v-if="loading">
    <UiSkeleton :count="6" />
  </div>

  <template v-else>
    <!-- Stat cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
      <UiStatCard
        :label="t('gamif.my_points')"
        :value="(stats?.total_points ?? 0).toString()"
      />
      <UiStatCard
        :label="t('gamif.my_rank')"
        :value="stats?.rank_total ? `#${stats.rank_total}` : t('gamif.no_rank')"
      />
      <UiStatCard
        :label="t('gamif.title')"
        :value="t('gamif.badges_count', { n: stats?.badges_count ?? 0 })"
      />
    </div>

    <!-- Earned badges -->
    <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
      {{ t('gamif.earned') }}
    </h2>
    <div
      v-if="earnedBadges.length === 0"
      class="text-[13px] text-muted-foreground mb-6 italic"
    >
      —
    </div>
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6"
    >
      <UiCard v-for="ub in earnedBadges" :key="ub.badge.id" class="p-4">
        <div class="flex items-start gap-3">
          <div
            class="w-12 h-12 rounded-md bg-foreground text-background grid place-items-center text-[20px] shrink-0"
          >
            ★
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5 flex-wrap">
              <span class="text-[14px] font-semibold">{{ ub.badge.title }}</span>
              <UiBadge variant="default">{{ catLabel(ub.badge.category) }}</UiBadge>
            </div>
            <p class="text-[12px] text-muted-foreground mb-1">
              {{ ub.badge.description }}
            </p>
            <p class="text-[11px] font-mono text-muted-foreground">
              {{ t('gamif.awarded_on', { date: fmtDate(ub.awarded_at) }) }}
            </p>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- Locked catalog -->
    <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
      {{ t('gamif.catalog') }}
    </h2>
    <div
      v-if="lockedBadges.length === 0"
      class="text-[13px] text-muted-foreground mb-6 italic"
    >
      —
    </div>
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-8"
    >
      <UiCard
        v-for="b in lockedBadges"
        :key="b.id"
        class="p-4 opacity-60"
      >
        <div class="flex items-start gap-3">
          <div
            class="w-12 h-12 rounded-md bg-muted text-muted-foreground grid place-items-center text-[20px] shrink-0"
          >
            ☆
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5 flex-wrap">
              <span class="text-[14px] font-semibold">{{ b.title }}</span>
              <UiBadge variant="default">{{ catLabel(b.category) }}</UiBadge>
            </div>
            <p class="text-[12px] text-muted-foreground mb-1">
              {{ b.description }}
            </p>
            <p class="text-[11px] font-mono text-muted-foreground italic">
              {{ t('gamif.locked') }} ·
              {{ t('gamif.points_reward', { n: b.points_reward }) }}
            </p>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- Leaderboard -->
    <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
      {{ t('gamif.leaderboard') }}
    </h2>
    <div class="flex gap-2 mb-3 text-[12px]">
      <button
        v-for="s in ['total', 'weekly', 'monthly'] as const"
        :key="s"
        type="button"
        class="px-3 py-1.5 rounded-md font-mono uppercase tracking-wider transition-colors"
        :class="
          scope === s
            ? 'bg-foreground text-background'
            : 'border border-border text-muted-foreground hover:text-foreground'
        "
        @click="scope = s"
      >
        {{ t(`gamif.scope_${s}`) }}
      </button>
    </div>

    <UiCard no-padding>
      <table class="w-full text-[13px]">
        <thead>
          <tr class="border-b border-border text-left text-[11px] font-mono uppercase text-muted-foreground">
            <th class="px-4 py-2.5 w-12">{{ t('gamif.col_rank') }}</th>
            <th class="px-4 py-2.5">{{ t('gamif.col_name') }}</th>
            <th class="px-4 py-2.5 text-right">{{ t('gamif.col_points') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in leaderboard?.items ?? []"
            :key="row.user_id"
            class="border-b border-border last:border-0"
            :class="row.user_id === auth.user?.id ? 'bg-muted/50' : ''"
          >
            <td class="px-4 py-3 font-mono">#{{ row.rank }}</td>
            <td class="px-4 py-3">
              {{ row.full_name }}
              <span
                v-if="row.user_id === auth.user?.id"
                class="text-[11px] font-mono text-muted-foreground ml-1"
              >
                ({{ t('gamif.me_label') }})
              </span>
            </td>
            <td class="px-4 py-3 font-mono text-right">{{ row.points }}</td>
          </tr>
          <tr
            v-if="!leaderboard?.items?.length"
            class="border-b border-border last:border-0"
          >
            <td colspan="3" class="px-4 py-6 text-center text-muted-foreground">
              —
            </td>
          </tr>
        </tbody>
      </table>
    </UiCard>
  </template>
</template>
