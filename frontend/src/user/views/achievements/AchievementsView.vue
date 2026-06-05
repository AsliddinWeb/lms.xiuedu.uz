<script setup lang="ts">
/**
 * Yutuqlar sahifasi — Phase 11e (qayta ishlangan: sabab + progress).
 *
 * Har nishon real jarayonga bog'langan:
 *   - Olingan nishonlar — ANIQ sabab bilan (qaysi kurs/dars/imtihon uchun)
 *   - Olinmaganlar — progress (masalan 1/5) bilan: nimaga qancha qolgani
 *   - Leaderboard (scope toggle)
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
  type BadgeProgressItem,
  type LeaderboardResponse,
  type MyGamificationStats,
} from '@shared/api/gamification'
import { extractErrorMessage } from '@shared/api/client'
import { intlLocale } from '@shared/i18n'
import { useAuthStore } from '@shared/stores/auth'
import BadgeMedal from './BadgeMedal.vue'

const { t, locale } = useI18n()
const auth = useAuthStore()

const stats = ref<MyGamificationStats | null>(null)
const progress = ref<BadgeProgressItem[]>([])
const leaderboard = ref<LeaderboardResponse | null>(null)
const scope = ref<'total' | 'weekly' | 'monthly'>('total')
const loading = ref(true)
const error = ref<string | null>(null)

const earned = computed(() => progress.value.filter((b) => b.earned))
const locked = computed(() => progress.value.filter((b) => !b.earned))

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [s, prog, lb] = await Promise.all([
      gamificationApi.myStats(),
      gamificationApi.myProgress(),
      gamificationApi.leaderboard(scope.value, 20),
    ])
    stats.value = s
    progress.value = prog
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

function fmtDate(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString(intlLocale(locale.value))
  } catch {
    return new Date(iso).toLocaleDateString()
  }
}

function catLabel(code: string): string {
  return t(`gamif.category_${code}`)
}

function pct(b: BadgeProgressItem): number {
  if (b.target <= 0) return 0
  return Math.min(100, Math.round((b.current / b.target) * 100))
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

    <!-- Earned badges (sabab bilan) -->
    <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
      {{ t('gamif.earned') }}
    </h2>
    <div
      v-if="earned.length === 0"
      class="text-[13px] text-muted-foreground mb-6 italic"
    >
      {{ t('gamif.empty_earned') }}
    </div>
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-7"
    >
      <UiCard v-for="b in earned" :key="b.badge.id" class="p-4">
        <div class="flex items-start gap-3">
          <BadgeMedal :category="b.badge.category" :earned="true" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <span class="text-[14px] font-semibold">{{ b.badge.title }}</span>
              <UiBadge variant="success">{{ catLabel(b.badge.category) }}</UiBadge>
            </div>
            <!-- ANIQ sabab (real jarayonga bog'liq), bo'lmasa mezon -->
            <p class="text-[12px] text-foreground/80 mb-1.5 leading-snug">
              {{ b.reason || b.badge.description }}
            </p>
            <p class="text-[11px] font-mono text-muted-foreground">
              <span class="text-[#b8923c]">+{{ b.badge.points_reward }}</span>
              · {{ t('gamif.awarded_on', { date: fmtDate(b.awarded_at) }) }}
            </p>
          </div>
        </div>
      </UiCard>
    </div>

    <!-- Locked — progress bilan (sababli yo'l) -->
    <h2 class="text-[14px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
      {{ t('gamif.in_progress') }}
    </h2>
    <div
      v-if="locked.length === 0"
      class="text-[13px] text-muted-foreground mb-6 italic"
    >
      {{ t('gamif.empty_locked') }}
    </div>
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-8"
    >
      <UiCard v-for="b in locked" :key="b.badge.id" class="p-4">
        <div class="flex items-start gap-3">
          <BadgeMedal :category="b.badge.category" :earned="false" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <span class="text-[14px] font-semibold text-foreground/90">
                {{ b.badge.title }}
              </span>
              <UiBadge variant="default">{{ catLabel(b.badge.category) }}</UiBadge>
            </div>
            <p class="text-[12px] text-muted-foreground mb-2.5 leading-snug">
              {{ b.badge.description }}
            </p>
            <!-- Progress bar -->
            <div class="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-[#c19a3e] to-[#d9b962] transition-all"
                :style="{ width: `${pct(b)}%` }"
              ></div>
            </div>
            <div class="flex items-center justify-between mt-1.5">
              <span class="text-[11px] font-mono text-muted-foreground">
                {{ b.current }} / {{ b.target }}
              </span>
              <span class="text-[11px] font-mono text-muted-foreground">
                {{ t('gamif.points_reward', { n: b.badge.points_reward }) }}
              </span>
            </div>
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
