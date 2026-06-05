/**
 * Gamification API klient — Phase 11e.
 */
import { apiClient } from './client'

export interface BadgePublic {
  id: number
  code: string
  title: string
  description: string | null
  category: string
  icon_url: string | null
  points_reward: number
  is_hidden: boolean
}

export interface UserBadgeItem {
  badge: BadgePublic
  awarded_at: string
  context: Record<string, unknown> | null
}

export interface BadgeProgressItem {
  badge: BadgePublic
  earned: boolean
  awarded_at: string | null
  current: number
  target: number
  reason: string | null
}

export interface MyGamificationStats {
  total_points: number
  weekly_points: number
  monthly_points: number
  rank_total: number | null
  rank_weekly: number | null
  badges_count: number
  recent_badges: UserBadgeItem[]
}

export interface LeaderboardItem {
  user_id: number
  full_name: string
  avatar_url: string | null
  points: number
  rank: number
}

export interface LeaderboardResponse {
  scope: 'total' | 'weekly' | 'monthly'
  items: LeaderboardItem[]
  me_rank: number | null
  me_points: number | null
}

export const gamificationApi = {
  async myStats(): Promise<MyGamificationStats> {
    const { data } = await apiClient.get<MyGamificationStats>('/me/gamification')
    return data
  },

  async myBadges(): Promise<UserBadgeItem[]> {
    const { data } = await apiClient.get<UserBadgeItem[]>('/me/gamification/badges')
    return data
  },

  async badgeCatalog(): Promise<BadgePublic[]> {
    const { data } = await apiClient.get<BadgePublic[]>('/gamification/badges')
    return data
  },

  async myProgress(): Promise<BadgeProgressItem[]> {
    const { data } = await apiClient.get<BadgeProgressItem[]>(
      '/me/gamification/progress',
    )
    return data
  },

  async leaderboard(
    scope: 'total' | 'weekly' | 'monthly' = 'total',
    limit = 20,
  ): Promise<LeaderboardResponse> {
    const { data } = await apiClient.get<LeaderboardResponse>(
      '/gamification/leaderboard',
      { params: { scope, limit } },
    )
    return data
  },
}
