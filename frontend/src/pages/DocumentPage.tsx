import { ChevronLeft, ExternalLink } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router'

import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { DocumentPreview } from '@/features/documents/DocumentPreview'
import { formatBytes, formatDate } from '@/features/documents/format'
import { StatusBadge } from '@/features/documents/StatusBadge'
import { useDocument } from '@/features/documents/useDocument'
import { ApiError } from '@/lib/api'

const card = 'flex flex-col gap-3 rounded-xl border border-border bg-card p-5'

export function DocumentPage() {
  const { id = '' } = useParams()
  const location = useLocation()
  const back = (location.state as { back?: string } | null)?.back ?? '/documents'
  const { data: doc, isPending, isError, error } = useDocument(id)

  const backLink = (
    <Link
      to={back}
      className="inline-flex h-9 items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
    >
      <ChevronLeft aria-hidden="true" className="size-4" />
      Lab documents
    </Link>
  )

  if (isPending) {
    return (
      <div className="flex flex-col gap-6" aria-label="Loading document">
        {backLink}
        <Skeleton className="h-12 w-2/3" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError) {
    // 404: deleted or unknown; 422: not a valid ID in the URL
    const gone = error instanceof ApiError && [404, 422].includes(error.status)
    return (
      <div className="flex flex-col gap-4">
        {backLink}
        <h1 className="font-serif text-4xl">
          {gone ? 'Document not found' : "We couldn't load this document"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {gone ? 'It may have been deleted.' : error.message}
        </p>
      </div>
    )
  }

  const working = doc.status === 'pending' || doc.status === 'processing'

  return (
    <div className="flex flex-col gap-6">
      {backLink}

      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex min-w-0 flex-col gap-2">
          <h1 className="font-serif text-4xl leading-tight break-words md:text-5xl">{doc.title}</h1>
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="font-mono break-all">{doc.filename}</span>
            <span aria-hidden="true">·</span>
            <StatusBadge status={doc.status} error={doc.error_message} />
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={`/api/documents/${doc.id}/file`}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: 'outline', size: 'lg' })}
          >
            <ExternalLink aria-hidden="true" />
            Open original
          </a>
        </div>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <DocumentPreview doc={doc} />

        <aside aria-label="About this file" className="flex flex-col gap-4">
          <section className={card}>
            <h2 className="text-sm font-semibold">Summary</h2>
            {doc.summary ? (
              <>
                <p className="text-sm leading-relaxed">{doc.summary}</p>
                <p className="text-xs text-muted-foreground">
                  Written by the lab assistant when the file was indexed
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                {working ? 'The summary appears once indexing finishes.' : 'No summary for this file.'}
              </p>
            )}
          </section>


          <section className={card}>
            <h2 className="text-sm font-semibold">Details</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-muted-foreground">Type</dt>
              <dd className="uppercase">{doc.file_type}</dd>
              <dt className="text-muted-foreground">Size</dt>
              <dd>{formatBytes(doc.size_bytes)}</dd>
              <dt className="text-muted-foreground">Uploaded by</dt>
              <dd>{doc.uploaded_by_name ?? '—'}</dd>
              <dt className="text-muted-foreground">Added</dt>
              <dd>{formatDate(doc.created_at)}</dd>
              <dt className="text-muted-foreground">Indexed</dt>
              <dd>
                {doc.indexed_at
                  ? `${formatDate(doc.indexed_at)} · ${doc.passage_count} ${doc.passage_count === 1 ? 'passage' : 'passages'}`
                  : '—'}
              </dd>
            </dl>
          </section>
        </aside>
      </div>
    </div>
  )
}
