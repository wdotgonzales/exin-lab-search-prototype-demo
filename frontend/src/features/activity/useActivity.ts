import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'

export type ActivityGroup = 'signins' | 'uploads' | 'deletes' | 'accounts'

export type AuditEntry = {
  id: string
  created_at: string
  actor_email: string | null
  actor_known: boolean
  action: string
  target_type: string | null
  target_label: string | null
  metadata: Record<string, unknown>
  ip_address: string | null
}

export const ACTIVITY_PAGE_SIZE = 10

export function useActivity(group: ActivityGroup | null, page: number, enabled: boolean) {
  return useQuery({
    queryKey: ['activity', { group, page }],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(ACTIVITY_PAGE_SIZE),
        offset: String((page - 1) * ACTIVITY_PAGE_SIZE),
      })
      if (group) params.set('group', group)
      return api<{ items: AuditEntry[]; total: number }>(`/admin/audit-logs?${params}`)
    },
    placeholderData: keepPreviousData,
    enabled,
  })
}
