import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api'

import { documentsKey } from './useDocuments'

export type DeleteResult = { deleted: string[]; not_found: string[] }

export function useDeleteDocuments() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) =>
      api<DeleteResult>('/documents/delete', {
        method: 'POST',
        body: JSON.stringify({ document_ids: ids }),
      }),
    // refresh the list either way, so it always matches the server
    onSettled: () => queryClient.invalidateQueries({ queryKey: documentsKey }),
  })
}
