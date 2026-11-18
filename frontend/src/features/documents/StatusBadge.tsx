import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

import { STATUS_INFO } from './status'
import type { DocumentStatus } from './useDocuments'

const PILL =
  'inline-flex h-6 w-fit items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium whitespace-nowrap'

/** The badge on its own (used in the legend). */
export function StatusPill({ status }: { status: DocumentStatus }) {
  const s = STATUS_INFO[status]
  return (
    <span className={cn(PILL, s.badge)}>
      <span aria-hidden="true" className={cn('size-1.5 rounded-full', s.dot)} />
      {s.label}
    </span>
  )
}

/** The badge in the table: hover or keyboard focus shows what it means. */
export function StatusBadge({ status, error }: { status: DocumentStatus; error?: string | null }) {
  const s = STATUS_INFO[status]
  const detail = status === 'failed' && error ? error : s.hint
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className={cn(PILL, 'cursor-default', s.badge)}>
          <span aria-hidden="true" className={cn('size-1.5 rounded-full', s.dot)} />
          {s.label}
        </button>
      </TooltipTrigger>
      <TooltipContent side="left" className="max-w-64">
        <p className="font-medium">{s.label}</p>
        <p className="opacity-80">{detail}</p>
      </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
