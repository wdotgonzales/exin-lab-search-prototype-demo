import { useQuery } from '@tanstack/react-query'

import { documentKey } from './useDocument'

/** The raw file as text (for Markdown and TXT), from our own API. */
export function useDocumentContentText(id: string) {
  return useQuery({
    queryKey: [...documentKey(id), 'content-text'],
    queryFn: async () => {
      const res = await fetch(`/api/documents/${id}/content`, { credentials: 'include' })
      if (!res.ok) throw new Error(`Could not load the file (${res.status}).`)
      return res.text()
    },
    staleTime: Infinity,
    retry: false,
  })
}
