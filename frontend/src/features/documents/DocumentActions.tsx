import { Download, Link2, MoreHorizontal, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useMe } from '@/features/auth/useAuth'

import { useDeleteDocuments } from './useDeleteDocuments'
import type { DocumentDetail } from './useDocument'

type Props = { doc: DocumentDetail; back: string }

export function DocumentActions({ doc, back }: Props) {
  const { data: me } = useMe()
  const isAdmin = me?.role === 'admin'
  const navigate = useNavigate()
  const remove = useDeleteDocuments()
  const [confirming, setConfirming] = useState(false)

  const download = () => {
    const link = document.createElement('a')
    link.href = `/api/documents/${doc.id}/content`
    link.download = doc.filename
    link.click()
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      toast.success('Link copied')
    } catch {
      toast.error("Couldn't copy the link")
    }
  }

  const confirmDelete = () =>
    remove.mutate([doc.id], {
      onSuccess: () => {
        toast.success('File deleted')
        navigate(back, { replace: true }) // Back can't return to a deleted page
      },
      onError: (error) => toast.error(error.message || 'Delete failed. Try again.'),
    })

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="More actions"
          className={buttonVariants({ variant: 'outline', size: 'icon-lg' })}
        >
          <MoreHorizontal aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={download}>
            <Download aria-hidden="true" />
            Download
          </DropdownMenuItem>
          <DropdownMenuItem onClick={copyLink}>
            <Link2 aria-hidden="true" />
            Copy link
          </DropdownMenuItem>
          {isAdmin && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onClick={() => setConfirming(true)}>
                <Trash2 aria-hidden="true" />
                Delete file…
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={confirming} onOpenChange={(open) => !remove.isPending && setConfirming(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this file?</DialogTitle>
            <DialogDescription>
              The file and its search index will be removed. The lab assistant won't find it
              anymore. This can't be undone.
            </DialogDescription>
          </DialogHeader>
          <p className="truncate rounded-lg border border-border bg-card/40 px-3 py-2 font-mono text-xs">
            {doc.filename}
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              autoFocus
              disabled={remove.isPending}
              onClick={() => setConfirming(false)}
            >
              No, keep it
            </Button>
            <Button variant="destructive" disabled={remove.isPending} onClick={confirmDelete}>
              {remove.isPending ? 'Deleting…' : 'Yes, delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
