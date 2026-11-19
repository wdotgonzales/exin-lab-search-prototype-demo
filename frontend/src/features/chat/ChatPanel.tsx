import { AlertCircle, ArrowUp, Clock, ExternalLink, Info, List } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { SheetDescription, SheetTitle } from '@/components/ui/sheet'

import type { AskAction } from './api'
import { AnswerText } from './AnswerText'
import { SourceCard } from './SourceCard'
import type { ChatMessage, useChat } from './useChat'

// More sources than this are shown as one-line rows, so the answer stays readable.
const COMPACT_AFTER = 3

const EXAMPLES = [
  'What was uploaded this week?',
  'Summarize each document',
  'What problems or issues are mentioned in the documents?',
  'Write a short email summarizing the latest results',
]

type Props = {
  chat: ReturnType<typeof useChat>
  onClose: () => void
}

export function ChatPanel({ chat, onClose }: Props) {
  const navigate = useNavigate()
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: 'end' })
  }, [chat.messages.length, chat.pending])

  function submit() {
    if (!draft.trim() || chat.pending) return
    chat.send(draft)
    setDraft('')
  }

  function showInList(filename: string) {
    navigate(`/documents?q=${encodeURIComponent(filename)}`)
    onClose()
  }

  function runAction(action: AskAction) {
    if (action.type === 'show_in_list') showInList(action.query)
  }

  function cite(messageId: number, n: number) {
    document
      .getElementById(sourceId(messageId, n))
      ?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
  }

  return (
    <>
      <header className="flex items-center gap-3 border-b py-4 pr-12 pl-5">
        <div className="flex min-w-0 flex-col gap-0.5">
          <SheetTitle className="text-[15px]">Lab assistant</SheetTitle>
          <SheetDescription className="text-xs">
            Answers from your lab's documents
          </SheetDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="ml-auto"
          onClick={() => {
            chat.reset()
            inputRef.current?.focus()
          }}
          disabled={chat.messages.length === 0 && !chat.pending}
        >
          New chat
        </Button>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
        {chat.messages.length === 0 && !chat.pending ? (
          <EmptyState onPick={chat.send} />
        ) : (
          chat.messages.map((message) => (
            <Message
              key={message.id}
              message={message}
              pending={chat.pending}
              onCite={(n) => cite(message.id, n)}
              onRetry={() => chat.retry(message.id)}
              onShowInList={showInList}
              onAction={runAction}
            />
          ))
        )}
        {chat.pending && (
          <div role="status" className="flex items-center gap-2.5 text-[13px] text-muted-foreground">
            <span aria-hidden="true" className="flex gap-1">
              <span className="size-1.5 animate-pulse rounded-full bg-primary" />
              <span className="size-1.5 animate-pulse rounded-full bg-primary/60 [animation-delay:150ms]" />
              <span className="size-1.5 animate-pulse rounded-full bg-primary/30 [animation-delay:300ms]" />
            </span>
            Searching the lab documents…
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="flex flex-col gap-2 border-t px-4 pt-3.5 pb-4"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <label htmlFor="chat-input" className="sr-only">
          Ask the lab assistant
        </label>
        <div className="flex items-end gap-2 rounded-xl border bg-card py-2 pr-2 pl-3.5 focus-within:ring-2 focus-within:ring-ring/50">
          <textarea
            id="chat-input"
            ref={inputRef}
            rows={2}
            maxLength={1000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                submit()
              }
            }}
            placeholder="Ask anything about the lab's documents…"
            className="flex-1 resize-none bg-transparent text-sm leading-relaxed outline-none placeholder:text-muted-foreground"
          />
          <Button
            type="submit"
            size="icon"
            aria-label="Send question"
            disabled={!draft.trim() || chat.pending}
          >
            <ArrowUp aria-hidden="true" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Enter to send · Shift+Enter for a new line · Check the sources before relying on an
          answer
        </p>
      </form>
    </>
  )
}

function sourceId(messageId: number, n: number) {
  return `chat-${messageId}-source-${n}`
}

function EmptyState({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="my-auto flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <h3 className="font-serif text-3xl leading-tight">Ask about the lab's documents</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Search across every uploaded file by meaning, not just keywords. Ask what the documents say, what was uploaded recently, or have it summarize, compare and draft notes. Every answer links to its sources.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium text-muted-foreground">Try asking</span>
        {EXAMPLES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-lg border bg-card px-3 py-2.5 text-left text-[13px] leading-snug hover:bg-accent"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

type MessageProps = {
  message: ChatMessage
  pending: boolean
  onCite: (n: number) => void
  onRetry: () => void
  onShowInList: (filename: string) => void
  onAction: (action: AskAction) => void
}

function Message({ message, pending, onCite, onRetry, onShowInList, onAction }: MessageProps) {
  if (message.role === 'user') {
    return (
      <div className="max-w-[82%] self-end rounded-2xl rounded-br-sm bg-muted px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-line">
        {message.text}
      </div>
    )
  }

  if (message.role === 'error' && message.kind === 'rate_limited') {
    return (
      <div
        role="alert"
        className="flex gap-2.5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3.5"
      >
        <Clock aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-300" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
            Question limit reached
          </p>
          <p className="text-[13px] leading-relaxed text-amber-900/80 dark:text-amber-100/80">
            {message.text} The limit keeps AI costs predictable for the lab.
          </p>
        </div>
      </div>
    )
  }

  if (message.role === 'error') {
    return (
      <div
        role="alert"
        className="flex flex-col gap-2.5 rounded-xl border border-destructive/40 bg-destructive/10 p-3.5"
      >
        <div className="flex gap-2.5">
          <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium text-destructive">
              The assistant couldn't answer just now
            </p>
            <p className="text-[13px] leading-relaxed text-muted-foreground">{message.text}</p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="ml-6.5 self-start" onClick={onRetry} disabled={pending}>
          Try again
        </Button>
      </div>
    )
  }

  if (message.status === 'no_sources') {
    return (
      <div className="flex flex-col gap-2 rounded-xl border border-dashed p-3.5">
        <p className="text-sm leading-relaxed">{message.text}</p>
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          Try other words, add a lab ID such as M-042, or upload the file that has the answer.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {message.generalKnowledge && (
        <p
          role="note"
          className="inline-flex items-center gap-1.5 self-start rounded-full border border-sky-500/35 bg-sky-500/10 px-2.5 py-1 text-xs font-medium text-sky-800 dark:text-sky-200"
        >
          <Info aria-hidden="true" className="size-3.5" />
          General knowledge, not from your lab's documents
        </p>
      )}
      <AnswerText text={message.text} onCite={onCite} />
      <div className="flex flex-col gap-2">
        {message.sources.map((source) => (
          <SourceCard
            key={source.n}
            id={sourceId(message.id, source.n)}
            source={source}
            onShowInList={onShowInList}
            compact={message.sources.length > COMPACT_AFTER}
          />
        ))}
      </div>
      {message.checked.length > 0 && (
        <p className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
          <span>Checked:</span>
          {message.checked.map((item) => (
            <span key={item} className="rounded-full border px-2 py-0.5">
              {item}
            </span>
          ))}
        </p>
      )}
      {message.actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {message.actions.map((action) => (
            <ActionButton key={action.label} action={action} onAction={onAction} />
          ))}
        </div>
      )}
    </div>
  )
}

/** A suggested next step. It only runs when the user clicks it. */
function ActionButton({
  action,
  onAction,
}: {
  action: AskAction
  onAction: (action: AskAction) => void
}) {
  const className = 'border-primary/50 bg-primary/10 hover:bg-primary/20'
  if (action.type === 'open_document') {
    return (
      <Button variant="outline" size="sm" className={className} asChild>
        <a href={`/api/documents/${action.document_id}/file`} target="_blank" rel="noopener noreferrer">
          <ExternalLink aria-hidden="true" />
          {action.label}
        </a>
      </Button>
    )
  }
  return (
    <Button variant="outline" size="sm" className={className} onClick={() => onAction(action)}>
      <List aria-hidden="true" />
      {action.label}
    </Button>
  )
}
