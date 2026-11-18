import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/button'

/** 1 … 4 5 6 … 12 style list of pages around the current one. */
function pageList(current: number, total: number): (number | '…')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const wanted = [1, total, current - 1, current, current + 1].filter((p) => p >= 1 && p <= total)
  const sorted = [...new Set(wanted)].sort((a, b) => a - b)
  const out: (number | '…')[] = []
  let previous = 0
  for (const p of sorted) {
    if (p - previous > 1) out.push('…')
    out.push(p)
    previous = p
  }
  return out
}

type Props = {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}

export function Pagination({ page, pageSize, total, onChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-card/40 px-4 py-3"
    >
      <span className="hidden text-sm text-muted-foreground md:inline">
        Showing {first}–{last} of {total}
      </span>
      <div className="ml-auto flex items-center gap-1.5">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          <ChevronLeft aria-hidden="true" />
          Previous
        </Button>
        <span className="hidden gap-1 md:flex">
          {pageList(page, totalPages).map((p, i) =>
            p === '…' ? (
              <span key={`gap-${i}`} className="px-2 text-sm text-muted-foreground">
                …
              </span>
            ) : (
              <Button
                key={p}
                size="sm"
                variant={p === page ? 'secondary' : 'ghost'}
                aria-current={p === page ? 'page' : undefined}
                className="w-9"
                onClick={() => onChange(p)}
              >
                {p}
              </Button>
            ),
          )}
        </span>
        <span className="px-2 text-sm text-muted-foreground md:hidden">
          Page {page} of {totalPages}
        </span>
        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>
          Next
          <ChevronRight aria-hidden="true" />
        </Button>
      </div>
    </nav>
  )
}
