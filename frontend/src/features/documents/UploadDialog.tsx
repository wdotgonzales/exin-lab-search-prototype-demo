import { FileUp, Upload, X } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

import { formatBytes } from './format'
import { ACCEPT, MAX_FILE_MB, MAX_FILES, validateFile } from './upload'

type Staged = { key: string; file: File; problem: string | null }

export function UploadDialog({ onUpload }: { onUpload: (files: File[]) => void }) {
  const [open, setOpen] = useState(false)
  const [staged, setStaged] = useState<Staged[]>([])
  const [dragging, setDragging] = useState(false)

  const ready = staged.filter((s) => !s.problem)
  const skipped = staged.length - ready.length
  const tooMany = ready.length > MAX_FILES

  function add(list: FileList | null) {
    if (!list) return
    const files = Array.from(list)
    setStaged((prev) => {
      const seen = new Set(prev.map((s) => s.key))
      const next = [...prev]
      for (const file of files) {
        const key = `${file.name}:${file.size}:${file.lastModified}`
        if (!seen.has(key)) {
          seen.add(key)
          next.push({ key, file, problem: validateFile(file) })
        }
      }
      return next
    })
  }

  function changeOpen(next: boolean) {
    setOpen(next)
    if (!next) setStaged([])
  }

  function submit() {
    onUpload(ready.map((s) => s.file))
    changeOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button size="lg">
          <Upload aria-hidden="true" />
          Upload files
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>Upload files</DialogTitle>
          <DialogDescription>
            PDF, DOCX, XLSX, CSV, MD or TXT · up to {MAX_FILE_MB} MB each
          </DialogDescription>
        </DialogHeader>

        <label
          htmlFor="upload-input"
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            add(e.dataTransfer.files)
          }}
          className={cn(
            'flex cursor-pointer flex-col items-center gap-2 rounded-xl border-[1.5px] border-dashed px-5 py-7 text-center transition-colors',
            dragging ? 'border-primary bg-primary/10' : 'border-primary/60 bg-primary/5',
          )}
        >
          <FileUp aria-hidden="true" className="size-6 text-primary" />
          <span className="text-sm font-medium">
            Drag files here, or <span className="text-primary underline">browse</span>
          </span>
          <span className="text-xs text-muted-foreground">You can add several files at once</span>
          <input
            id="upload-input"
            type="file"
            multiple
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => {
              add(e.target.files)
              e.target.value = ''
            }}
          />
        </label>

        {staged.length > 0 && (
          <ul aria-label="Files to upload" className="max-h-64 overflow-y-auto rounded-lg border border-border">
            {staged.map((s) => (
              <li
                key={s.key}
                className="flex items-center gap-3 border-b border-border py-2 pr-2 pl-3.5 last:border-b-0"
              >
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span
                    className={cn(
                      'truncate font-mono text-[13px]',
                      s.problem && 'text-muted-foreground line-through',
                    )}
                  >
                    {s.file.name}
                  </span>
                  {s.problem && <span className="text-xs text-destructive">{s.problem}</span>}
                </span>
                <span className="text-xs text-muted-foreground">{formatBytes(s.file.size)}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8"
                  aria-label={`Remove ${s.file.name}`}
                  onClick={() => setStaged((prev) => prev.filter((x) => x.key !== s.key))}
                >
                  <X aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}

        {tooMany && (
          <p role="alert" className="text-sm text-destructive">
            Pick at most {MAX_FILES} files at a time.
          </p>
        )}

        <DialogFooter className="items-center gap-3 sm:justify-between">
          <span className="text-sm text-muted-foreground">
            {ready.length} ready{skipped ? ` · ${skipped} skipped` : ''}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => changeOpen(false)}>
              Cancel
            </Button>
            <Button disabled={ready.length === 0 || tooMany} onClick={submit}>
              <Upload aria-hidden="true" />
              Upload {ready.length} {ready.length === 1 ? 'file' : 'files'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
