import { CircleCheck, CircleX, Info, X } from 'lucide-react'
import { useEffect } from 'react'

import { Button } from '@/components/ui/button'

import { FINISHED, type UploadItem } from './useUploadQueue'

const HIDE_AFTER_MS = 2500

export function UploadPanel({ items, onClose }: { items: UploadItem[]; onClose: () => void }) {
  const finished = items.filter((i) => FINISHED.includes(i.state)).length
  const allFinished = items.length > 0 && finished === items.length
  const allOk = items.every((i) => i.state === 'done')

  // Everything succeeded → hide by itself. Any problem → stay until closed.
  useEffect(() => {
    if (!allFinished || !allOk) return
    const timer = setTimeout(onClose, HIDE_AFTER_MS)
    return () => clearTimeout(timer)
  }, [allFinished, allOk, onClose])

  if (items.length === 0) return null

  return (
    <section aria-label="Uploads" className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <span className="text-sm font-semibold">
          {allFinished
            ? 'Uploads finished'
            : `Uploading ${items.length} ${items.length === 1 ? 'file' : 'files'}`}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {finished} of {items.length} finished
          </span>
          {allFinished && (
            <Button variant="ghost" size="icon" className="size-8" aria-label="Close uploads" onClick={onClose}>
              <X aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>

      <ul>
        {items.map((item) => (
          <li
            key={item.key}
            className="flex flex-col gap-2 border-b border-border px-4 py-3 text-sm last:border-b-0"
          >
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
              <span className="min-w-0 truncate font-mono text-[13px]">{item.name}</span>
              <span className="flex items-center gap-2 text-muted-foreground" role="status">
                {item.state === 'waiting' && 'Waiting…'}
                {item.state === 'uploading' && `${Math.round(item.progress * 100)}%`}
                {item.state === 'done' && (
                  <>
                    <CircleCheck aria-hidden="true" className="size-4 text-[#A9D1B9]" />
                    Uploaded
                  </>
                )}
                {item.state === 'skipped' && (
                  <>
                    <Info aria-hidden="true" className="size-4" />
                    {item.message}
                    {item.documentId && (
                      <a
                        href={`/api/documents/${item.documentId}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary underline"
                      >
                        Open
                      </a>
                    )}
                  </>
                )}
                {(item.state === 'rejected' || item.state === 'failed') && (
                  <span className="flex items-center gap-2 text-destructive">
                    <CircleX aria-hidden="true" className="size-4" />
                    {item.message}
                  </span>
                )}
              </span>
            </div>
            {item.state === 'uploading' && (
              <div className="h-1.5 overflow-hidden rounded-full bg-secondary" aria-hidden="true">
                <div
                  className="h-full bg-primary transition-[width]"
                  style={{ width: `${Math.round(item.progress * 100)}%` }}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
