import { ListFilter, X } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

import type { DocFilters } from './useDocuments'

const TYPES = ['pdf', 'docx', 'xlsx', 'csv', 'md', 'txt']
const pad = (n: number) => String(n).padStart(2, '0')
const isoDay = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

function preset(kind: 'today' | 'week' | 'month'): DocFilters {
  const today = new Date()
  const start = new Date(today)
  if (kind === 'week') start.setDate(today.getDate() - 6)
  if (kind === 'month') start.setDate(1)
  return { from: isoDay(start), to: isoDay(today) }
}

const fmt = (day: string) =>
  new Date(`${day}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

function dateLabel(from?: string, to?: string) {
  if (from && to) return `${fmt(from)} – ${fmt(to)}`
  return from ? `From ${fmt(from)}` : `Until ${fmt(to ?? '')}`
}

type DialogProps = { value: DocFilters; active: number; onApply: (value: DocFilters) => void }

export function FilterDialog({ value, active, onApply }: DialogProps) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<DocFilters>(value)
  const invalid = Boolean(draft.from && draft.to && draft.from > draft.to)

  const openDialog = () => {
    setDraft(value)
    setOpen(true)
  }
  const apply = () => {
    onApply(draft)
    setOpen(false)
  }

  return (
    <>
      <Button
        variant="outline"
        aria-haspopup="dialog"
        onClick={openDialog}
        className={cn(active > 0 && 'border-primary bg-primary/10')}
      >
        <ListFilter aria-hidden="true" />
        Filter
        {active > 0 && (
          <span className="rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">
            {active}
          </span>
        )}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Filter documents</DialogTitle>
            <DialogDescription>
              Narrow the list by file type and when files were added.
            </DialogDescription>
          </DialogHeader>

          <fieldset className="flex flex-col">
            <legend className="mb-2.5 text-sm font-semibold">File type</legend>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[['', 'All types'], ...TYPES.map((t) => [t, t.toUpperCase()])].map(([type, label]) => {
                const checked = (draft.type ?? '') === type
                return (
                  <label
                    key={type || 'all'}
                    className={cn(
                      'flex h-11 cursor-pointer items-center gap-2.5 rounded-lg border border-border px-3 text-sm',
                      checked && 'border-primary bg-primary/10',
                    )}
                  >
                    <input
                      type="radio"
                      name="doc-type"
                      value={type}
                      checked={checked}
                      onChange={() => setDraft({ ...draft, type })}
                      className="size-4 accent-primary"
                    />
                    {label}
                  </label>
                )
              })}
            </div>
          </fieldset>

          <fieldset className="flex flex-col gap-2.5">
            <legend className="mb-2.5 text-sm font-semibold">Date added</legend>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="filter-from" className="text-xs text-muted-foreground">
                  From
                </label>
                <Input
                  id="filter-from"
                  type="date"
                  value={draft.from ?? ''}
                  onChange={(e) => setDraft({ ...draft, from: e.target.value })}
                  className="h-11 dark:[color-scheme:dark]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="filter-to" className="text-xs text-muted-foreground">
                  To
                </label>
                <Input
                  id="filter-to"
                  type="date"
                  value={draft.to ?? ''}
                  onChange={(e) => setDraft({ ...draft, to: e.target.value })}
                  className="h-11 dark:[color-scheme:dark]"
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['today', 'Today'],
                  ['week', 'Last 7 days'],
                  ['month', 'This month'],
                ] as const
              ).map(([kind, label]) => (
                <Button
                  key={kind}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-full"
                  onClick={() => setDraft({ ...draft, ...preset(kind) })}
                >
                  {label}
                </Button>
              ))}
            </div>
            {invalid && (
              <p role="alert" className="text-sm text-destructive">
                The start date must be on or before the end date.
              </p>
            )}
          </fieldset>

          <DialogFooter className="sm:justify-between">
            <Button variant="ghost" onClick={() => setDraft({})}>
              Clear all
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={apply} disabled={invalid}>
                Apply filters
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

type ChipsProps = { value: DocFilters; onChange: (value: DocFilters) => void }

export function ActiveFilterChips({ value, onChange }: ChipsProps) {
  const chips = []
  if (value.type) {
    chips.push({ key: 'type', label: value.type.toUpperCase(), next: { ...value, type: '' } })
  }
  if (value.from || value.to) {
    chips.push({
      key: 'date',
      label: dateLabel(value.from, value.to),
      next: { ...value, from: '', to: '' },
    })
  }
  return (
    <>
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex h-8 items-center gap-1 rounded-full border border-border pr-1 pl-3 text-sm"
        >
          {chip.label}
          <button
            type="button"
            aria-label={`Remove filter: ${chip.label}`}
            onClick={() => onChange(chip.next)}
            className="inline-flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X aria-hidden="true" className="size-3.5" />
          </button>
        </span>
      ))}
    </>
  )
}
