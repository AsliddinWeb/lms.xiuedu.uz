/**
 * Phase 8f — HEMIS sync log admin API client.
 */
import { apiClient } from '@shared/api/client'

export interface HemisSyncLogItem {
  id: number
  sync_type: string
  target_id: number | null
  status: string
  attempts: number
  payload: Record<string, unknown> | null
  response: Record<string, unknown> | null
  last_error: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedHemisSyncLogs {
  items: HemisSyncLogItem[]
  total: number
}

export const hemisApi = {
  async listSyncLog(
    params: {
      sync_type?: string
      status?: string
      target_id?: number
      page?: number
      page_size?: number
    } = {},
  ): Promise<PaginatedHemisSyncLogs> {
    return (
      await apiClient.get<PaginatedHemisSyncLogs>('/hemis/sync-log', { params })
    ).data
  },

  async retry(id: number): Promise<{ ok: boolean; status?: string }> {
    return (await apiClient.post<{ ok: boolean; status?: string }>(
      `/hemis/sync-log/${id}/retry`,
    )).data
  },

  // Phase 10f — manual data sync trigger (admin only)
  async runSync(
    entity: 'students' | 'employees' | 'departments' | 'groups' | 'all',
  ): Promise<{
    log_id: number
    sync_type: string
    status: string
    upserted: number
    failed: number
    total: number
    last_error: string | null
  }> {
    return (await apiClient.post(`/hemis/sync/${entity}`)).data
  },
}
