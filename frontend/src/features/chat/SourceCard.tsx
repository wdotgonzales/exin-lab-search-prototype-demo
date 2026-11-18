import { Copy, ExternalLink, List } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'

import type { AskSource } from './api'

type Props = {
  id: string
  source: AskSource
  onShowInList: (filename: string) => void
  /** One line per source: used when an answer cites many documents. */
  compact?: boolean
}

export function SourceCard({ id, source, onShowInList, compact = false }: Props) {
  async function copyName() {
    try {
      await navigator.clipboard.writeText(source.filename)
      toast.success(`Copied ${source.filename}`)
    } catch {
      toast.error("Couldn't copy the file name")
    }
  }

  const number = (
    <span className="flex size-5 shrink-0 items-center justify-center rounded bg-primary/15 text-[11px] font-semibold text-primary">
      {source.n}
    </span>
  )
  const openHref = `/api/documents/${source.document_id}/file`

  if (compact) {
    return (
      <article
        id={id}
        aria-label={`Source ${source.n}`}
        className="flex scroll-mt-4 items-center gap-2.5 rounded-lg border bg-card py-2 pr-1.5 pl-3"
      >
        {number}
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-[13px] font-medium">{source.title}</span>
          <span className="truncate font-mono text-[11px] text-muted-foreground">
            {source.filename}
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          aria-label={`Show ${source.title} in the list`}
          onClick={() => onShowInList(source.filename)}
        >
          <List aria-hidden="true" />
        </Button>
        <Button variant="ghost" size="icon" className="size-8" asChild>
          <a
            href={openHref}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open ${source.title}`}
          >
            <ExternalLink aria-hidden="true" />
          </a>
        </Button>
      </article>
    )
  }

  return (
    <article
      id={id}
      aria-label={`Source ${source.n}`}
      className="flex scroll-mt-4 flex-col gap-2.5 rounded-xl border bg-card p-3.5"
    >
      <div className="flex items-start gap-2.5">
        {number}
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-sm font-medium">{source.title}</span>
          <span className="truncate font-mono text-xs text-muted-foreground">
            {source.filename}
            {source.page_number ? ` · page ${source.page_number}` : ''}
          </span>
        </div>
      </div>
      {source.snippet && (
        <p className="border-l-2 pl-2.5 text-[13px] leading-relaxed text-muted-foreground">
          {source.snippet}
        </p>
      )}
      <div className="flex flex-wrap gap-1.5">
        <Button variant="outline" size="sm" onClick={() => onShowInList(source.filename)}>
          <List aria-hidden="true" />
          Show in list
        </Button>
        <Button variant="outline" size="sm" asChild>
          <a href={openHref} target="_blank" rel="noopener noreferrer">
            <ExternalLink aria-hidden="true" />
            Open
          </a>
        </Button>
        <Button variant="outline" size="sm" onClick={copyName}>
          <Copy aria-hidden="true" />
          Copy name
        </Button>
      </div>
    </article>
  )
}
