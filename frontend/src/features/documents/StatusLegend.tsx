import { Info } from 'lucide-react'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

import { STATUS_INFO, STATUS_ORDER } from './status'
import { StatusPill } from './StatusBadge'

export function StatusLegend() {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="What do the search statuses mean?"
          className="inline-flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground"
        >
          <Info aria-hidden="true" className="size-4" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80">
        <p className="text-sm font-medium">Search status</p>
        <p className="mt-1 mb-4 text-xs text-muted-foreground">
          Uploading only stores the file. The assistant can use it once it is Searchable.
        </p>
        <ul className="flex flex-col gap-3">
          {STATUS_ORDER.map((status) => (
            <li key={status} className="flex flex-col gap-1">
              <StatusPill status={status} />
              <span className="text-xs text-muted-foreground">{STATUS_INFO[status].hint}</span>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  )
}
