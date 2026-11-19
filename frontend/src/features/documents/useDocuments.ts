import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'

export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'failed'

export type DocumentItem = {
  id: string
  title: string
  filename: string
  file_type: string
  size_bytes: number | null
  status: DocumentStatus
  error_message: string | null
  uploaded_by_name: string | null
  created_at: string
}

export type DocumentList = { items: DocumentItem[]; total: number }

/** Local calendar days (YYYY-MM-DD) as the person picked them. */
export type DocFilters = { type?: string; from?: string; to?: string }

const startOfLocalDay = (day: string) => new Date(`${day}T00:00:00`)

export const PAGE_SIZE = 20
export const documentsKey = ['documents'] as const

const isWorking = (d: DocumentItem) => d.status === 'pending' || d.status === 'processing'

export function useDocuments(q: string, page: number, filters: DocFilters = {}) {
  return useQuery({
    queryKey: [...documentsKey, { q, page, ...filters }],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String((page - 1) * PAGE_SIZE),
      })
      if (q) params.set('q', q)
      if (filters.type) params.set('type', filters.type)
      // send local day boundaries as exact moments: [start of from, start of the day after to)
      if (filters.from) params.set('added_after', startOfLocalDay(filters.from).toISOString())
      if (filters.to) {
        const end = startOfLocalDay(filters.to)
        end.setDate(end.getDate() + 1)
        params.set('added_before', end.toISOString())
      }
      return api<DocumentList>(`/documents?${params}`)
    },
    // keep showing the old page while the next one loads (no flicker)
    placeholderData: keepPreviousData,
    // poll while anything is still being processed
    refetchInterval: (query) => (query.state.data?.items.some(isWorking) ? 5000 : false),
  })
}
