import { MessageSquare } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent } from '@/components/ui/sheet'

import { ChatPanel } from './ChatPanel'
import { useChat } from './useChat'

/**
 * The round chat button on every page, and the panel it opens.
 * It lives inside AppShell, so the conversation survives page changes, and it
 * is unmounted on sign-out, so the next person on this computer starts empty.
 */
export function ChatLauncher() {
  const [open, setOpen] = useState(false)
  const chat = useChat()

  return (
    <>
      <Button
        size="icon"
        aria-label="Open lab assistant"
        onClick={() => setOpen(true)}
        className="fixed right-6 bottom-6 z-40 size-14 rounded-full shadow-lg"
      >
        <MessageSquare aria-hidden="true" className="size-6" />
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          // Our panel focuses the question box itself.
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="flex flex-col gap-0 p-0 data-[side=right]:w-full data-[side=right]:sm:max-w-[440px]"
        >
          <ChatPanel chat={chat} onClose={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </>
  )
}
