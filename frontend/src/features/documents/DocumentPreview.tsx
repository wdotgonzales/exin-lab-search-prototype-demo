import { lazy, Suspense, useState } from 'react'

import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

import { ExtractedText } from './ExtractedText'
import { TableViewer } from './TableViewer'
import type { DocumentDetail } from './useDocument'
import { useDocumentContentText } from './useDocumentContent'

// Loaded only when someone opens a Markdown file
const MarkdownViewer = lazy(() => import('./MarkdownViewer'))
const DocxViewer = lazy(() => import('./DocxViewer'))

const PREVIEWABLE = new Set(['pdf', 'docx', 'xlsx', 'csv', 'md', 'txt'])

function TextViewer({ id }: { id: string }) {
  const { data, isPending, isError, error } = useDocumentContentText(id)
  if (isPending) return <Skeleton className="m-5 h-40" />
  if (isError) return <p className="p-5 text-sm text-muted-foreground">{error.message}</p>
  return (
    <pre className="max-h-[720px] overflow-auto p-5 font-mono text-xs leading-relaxed whitespace-pre-wrap">
      {data}
    </pre>
  )
}

function Preview({ doc }: { doc: DocumentDetail }) {
  switch (doc.file_type) {
    case 'pdf':
      // the browser's own PDF viewer: pages, zoom and search for free
      return (
        <iframe
          title={`${doc.title} (PDF preview)`}
          src={`/api/documents/${doc.id}/content`}
          className="h-[720px] w-full border-0 bg-white"
        />
      )
    case 'md':
      return (
        <Suspense fallback={<Skeleton className="m-5 h-40" />}>
          <MarkdownViewer id={doc.id} />
        </Suspense>
      )
    case 'docx':
      return (
        <Suspense fallback={<Skeleton className="m-5 h-40" />}>
          <DocxViewer id={doc.id} />
        </Suspense>
      )
    case 'xlsx':
    case 'csv':
      return <TableViewer id={doc.id} />
    case 'txt':
      return <TextViewer id={doc.id} />
    default:
      return null
  }
}

export function DocumentPreview({ doc }: { doc: DocumentDetail }) {
  const canPreview = PREVIEWABLE.has(doc.file_type)
  const [view, setView] = useState<'preview' | 'text'>(canPreview ? 'preview' : 'text')

  const toggle = (value: 'preview' | 'text', label: string) => (
    <button
      type="button"
      aria-pressed={view === value}
      onClick={() => setView(value)}
      className={cn(
        'h-8 rounded-md px-3 text-sm font-medium',
        view === value ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {label}
    </button>
  )

  return (
    <section
      aria-label="Document preview"
      className="flex min-w-0 flex-col overflow-hidden rounded-xl border border-border"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-card px-3 py-2">
        <div role="group" aria-label="View" className="flex gap-1 rounded-lg bg-background p-1">
          {canPreview && toggle('preview', 'Preview')}
          {toggle('text', 'Extracted text')}
        </div>
        <span className="px-1 text-xs text-muted-foreground">
          {view === 'text' ? 'What search and the lab assistant read' : 'The original file'}
        </span>
      </div>
      {view === 'preview' && canPreview ? <Preview doc={doc} /> : <ExtractedText id={doc.id} />}
    </section>
  )
}
