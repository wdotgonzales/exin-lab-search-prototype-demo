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

export const PAGE_SIZE = 20
export const documentsKey = ['documents'] as const

const isWorking = (d: DocumentItem) => d.status === 'pending' || d.status === 'processing'

export function useDocuments(q: string, page: number) {
  return useQuery({
    queryKey: [...documentsKey, { q, page }],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String((page - 1) * PAGE_SIZE),
      })
      if (q) params.set('q', q)
      return api<DocumentList>(`/documents?${params}`)
    },
    // keep showing the old page while the next one loads (no flicker)
    placeholderData: keepPreviousData,
    // poll while anything is still being processed
    refetchInterval: (query) => (query.state.data?.items.some(isWorking) ? 5000 : false),
  })
}
