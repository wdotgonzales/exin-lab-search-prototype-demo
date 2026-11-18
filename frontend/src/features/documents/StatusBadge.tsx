import { cn } from '@/lib/utils'

import type { DocumentStatus } from './useDocuments'

const STYLES: Record<DocumentStatus, { label: string; badge: string; dot: string }> = {
  pending: { label: 'Queued', badge: 'border-border text-muted-foreground', dot: 'bg-muted-foreground' },
  processing: { label: 'Processing', badge: 'border-primary/40 bg-primary/15 text-primary', dot: 'bg-primary' },
  // mouse green from our palette
  indexed: { label: 'Ready', badge: 'border-[#A9D1B9]/35 bg-[#A9D1B9]/12 text-[#A9D1B9]', dot: 'bg-[#A9D1B9]' },
  failed: { label: 'Failed', badge: 'border-destructive/40 bg-destructive/12 text-destructive', dot: 'bg-destructive' },
}

export function StatusBadge({ status, error }: { status: DocumentStatus; error?: string | null }) {
  const style = STYLES[status]
  return (
    <span
      title={status === 'failed' && error ? error : undefined}
      className={cn(
        'inline-flex h-6 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium whitespace-nowrap',
        style.badge,
      )}
    >
      <span aria-hidden="true" className={cn('size-1.5 rounded-full', style.dot)} />
      {style.label}
    </span>
  )
}
