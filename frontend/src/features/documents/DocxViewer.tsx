import { useQuery } from '@tanstack/react-query'
import { renderAsync } from 'docx-preview'
import { useEffect, useRef, useState } from 'react'

import { Skeleton } from '@/components/ui/skeleton'

import { documentKey } from './useDocument'

export default function DocxViewer({ id }: { id: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)
  const { data, isPending, isError, error } = useQuery({
    queryKey: [...documentKey(id), 'content-bytes'],
    queryFn: async () => {
      const res = await fetch(`/api/documents/${id}/content`, { credentials: 'include' })
      if (!res.ok) throw new Error(`Could not load the file (${res.status}).`)
      return res.arrayBuffer()
    },
    staleTime: Infinity,
    retry: false,
  })

  useEffect(() => {
    const el = container.current
    if (!data || !el) return
    let cancelled = false
    renderAsync(data, el, undefined, {
      inWrapper: true, // white pages on a grey background
      breakPages: true,
      ignoreLastRenderedPageBreak: true,
    }).catch(() => {
      if (!cancelled) setFailed(true)
    })
    return () => {
      cancelled = true
      el.replaceChildren()
    }
  }, [data])

  return (
    <div className="max-h-[720px] overflow-auto">
      {isPending && <Skeleton className="m-5 h-40" />}
      {(isError || failed) && (
        <p className="p-5 text-sm text-muted-foreground">
          {isError ? error.message : 'This Word file could not be displayed.'} Try Extracted text
          or Open original.
        </p>
      )}
      <div ref={container} />
    </div>
  )
}
