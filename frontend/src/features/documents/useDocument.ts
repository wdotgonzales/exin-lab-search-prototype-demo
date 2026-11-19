import { useQuery } from '@tanstack/react-query'

import { api, ApiError } from '@/lib/api'

import type { DocumentItem } from './useDocuments'

export type LabId = { code: string; entity_type: string; mentions: number }

export type DocumentDetail = DocumentItem & {
  summary: string | null
  indexed_at: string | null
  passage_count: number
  lab_ids: LabId[]
}

export type TextSection = { label: string | null; page: number | null; text: string }
export type DocumentText = { sections: TextSection[]; truncated: boolean }

// Own key (not under ['documents']) so list refreshes don't refetch a deleted file.
export const documentKey = (id: string) => ['document', id] as const

const notFound = (error: unknown) =>
  error instanceof ApiError && [404, 422].includes(error.status)

export function useDocument(id: string) {
  return useQuery({
    queryKey: documentKey(id),
    queryFn: () => api<DocumentDetail>(`/documents/${id}`),
    retry: (count, error) => !notFound(error) && count < 2,
    // poll while it is still being indexed
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'processing' ? 5000 : false
    },
  })
}

export function useDocumentText(id: string) {
  return useQuery({
    queryKey: [...documentKey(id), 'text'],
    queryFn: () => api<DocumentText>(`/documents/${id}/text`),
    staleTime: Infinity, // a file's text never changes
    retry: false,
  })
}
