import { ChevronDown, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button, buttonVariants } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import { useDeleteDocuments } from './useDeleteDocuments'
import type { DocumentItem } from './useDocuments'

const files = (n: number) => `${n} ${n === 1 ? 'file' : 'files'}`

type Props = { selected: DocumentItem[]; onClear: () => void }

export function DeleteSelectedBar({ selected, onClear }: Props) {
  const [confirming, setConfirming] = useState(false)
  const remove = useDeleteDocuments()
  const label = files(selected.length)

  const confirm = () =>
    remove.mutate(
      selected.map((d) => d.id),
      {
        onSuccess: (result) => {
          toast.success(`${files(result.deleted.length)} deleted`)
          setConfirming(false)
          onClear()
        },
        onError: (error) => toast.error(error.message || 'Delete failed. Try again.'),
      },
    )

  return (
    <div
      role="region"
      aria-label="Selection"
      className="flex flex-wrap items-center gap-3 border-b border-primary/40 bg-primary/10 px-4 py-3"
    >
      <span className="text-sm font-semibold">{selected.length} selected</span>
      <Button variant="ghost" size="sm" onClick={onClear}>
        Clear selection
      </Button>

      <div className="ml-auto">
        <DropdownMenu>
          <DropdownMenuTrigger className={buttonVariants({ variant: 'outline' })}>
            Actions
            <ChevronDown aria-hidden="true" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem variant="destructive" onClick={() => setConfirming(true)}>
              <Trash2 aria-hidden="true" />
              Delete {label}…
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={confirming} onOpenChange={(open) => !remove.isPending && setConfirming(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {label}?</DialogTitle>
            <DialogDescription>
              These files and their search index will be removed. The lab assistant won't find
              them anymore. This can't be undone.
            </DialogDescription>
          </DialogHeader>
          <ul className="flex max-h-48 flex-col gap-1 overflow-y-auto rounded-lg border border-border bg-card/40 px-3 py-2 font-mono text-xs">
            {selected.map((d) => (
              <li key={d.id} className="truncate">
                {d.filename}
              </li>
            ))}
          </ul>
          <DialogFooter>
            <Button
              variant="outline"
              autoFocus
              disabled={remove.isPending}
              onClick={() => setConfirming(false)}
            >
              Cancel
            </Button>
            <Button variant="destructive" disabled={remove.isPending} onClick={confirm}>
              {remove.isPending ? 'Deleting…' : `Yes, delete ${label}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
