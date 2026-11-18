import { ListFilter } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useMe } from '@/features/auth/useAuth'
import { formatBytes, formatDate } from '@/features/documents/format'
import { Pagination } from '@/features/documents/Pagination'
import { StatusBadge } from '@/features/documents/StatusBadge'
import { PAGE_SIZE, useDocuments } from '@/features/documents/useDocuments'
import { useDebouncedValue } from '@/lib/useDebouncedValue'

const COLUMNS_HIDDEN_ON_PHONES = 'hidden md:table-cell'

export function DocumentsPage() {
  const { data: me } = useMe()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const page = Math.max(1, Number(params.get('page')) || 1)

  const [text, setText] = useState(q)
  const debounced = useDebouncedValue(text, 300)

  // Typing (after the pause) updates the URL and jumps back to page 1.
  useEffect(() => {
    const value = debounced.trim()
    if (value === q) return
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value) next.set('q', value)
        else next.delete('q')
        next.delete('page')
        return next
      },
      { replace: true },
    )
  }, [debounced, q, setParams])

  const goToPage = (p: number) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (p > 1) next.set('page', String(p))
      else next.delete('page')
      return next
    })

  const { data, isPending, isError, refetch, isRefetching } = useDocuments(q, page)

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs tracking-[0.14em] text-primary uppercase">Documents</p>
        <h1 className="font-serif text-5xl leading-tight">Lab documents</h1>
        <p className="text-sm text-muted-foreground">
          {data ? `${data.total} ${data.total === 1 ? 'file' : 'files'}` : ' '}
        </p>
      </div>

      <section aria-label="All documents" className="overflow-hidden rounded-xl border border-border">
        <div className="flex flex-wrap items-center gap-3 border-b border-border bg-card/40 px-4 py-3">
          <div className="relative w-full max-w-md">
            <label htmlFor="doc-filter" className="sr-only">
              Filter documents by title or filename
            </label>
            <ListFilter
              aria-hidden="true"
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              id="doc-filter"
              type="search"
              placeholder="Filter by title or filename"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {isPending ? (
          <div className="flex flex-col gap-3 p-4" aria-label="Loading documents">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center gap-3 px-4 py-12 text-center text-sm text-muted-foreground">
            <p>We couldn't load the documents.</p>
            <Button variant="outline" onClick={() => refetch()} disabled={isRefetching}>
              {isRefetching ? 'Retrying…' : 'Retry'}
            </Button>
          </div>
        ) : data.items.length === 0 ? (
          <div className="flex flex-col items-center gap-3 px-4 py-12 text-center text-sm text-muted-foreground">
            {q ? (
              <>
                <p>No documents match “{q}”.</p>
                <Button variant="outline" onClick={() => setText('')}>
                  Clear filter
                </Button>
              </>
            ) : (
              <p>
                No documents yet.
                {me?.role === 'admin' ? ' Use Upload files to add the first ones.' : ''}
              </p>
            )}
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead className={COLUMNS_HIDDEN_ON_PHONES}>Type</TableHead>
                  <TableHead className={COLUMNS_HIDDEN_ON_PHONES}>Size</TableHead>
                  <TableHead className={COLUMNS_HIDDEN_ON_PHONES}>Uploaded by</TableHead>
                  <TableHead className={COLUMNS_HIDDEN_ON_PHONES}>Added</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="w-full max-w-0">
                      <a
                        href={`/api/documents/${doc.id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate font-medium hover:text-primary"
                      >
                        {doc.title}
                      </a>
                      <span className="block truncate font-mono text-xs text-muted-foreground">
                        {doc.filename}
                      </span>
                    </TableCell>
                    <TableCell className={`${COLUMNS_HIDDEN_ON_PHONES} text-muted-foreground uppercase`}>
                      {doc.file_type}
                    </TableCell>
                    <TableCell className={`${COLUMNS_HIDDEN_ON_PHONES} text-muted-foreground`}>
                      {formatBytes(doc.size_bytes)}
                    </TableCell>
                    <TableCell className={`${COLUMNS_HIDDEN_ON_PHONES} text-muted-foreground`}>
                      {doc.uploaded_by_name ?? '—'}
                    </TableCell>
                    <TableCell className={`${COLUMNS_HIDDEN_ON_PHONES} whitespace-nowrap text-muted-foreground`}>
                      {formatDate(doc.created_at)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={doc.status} error={doc.error_message} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={goToPage} />
          </>
        )}
      </section>
    </div>
  )
}
