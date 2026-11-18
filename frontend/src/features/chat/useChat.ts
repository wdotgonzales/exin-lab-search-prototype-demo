import { useMutation } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'

import { ApiError } from '@/lib/api'

import { askQuestion, type AskAction, type AskSource, type HistoryTurn } from './api'

export type ChatMessage =
  | { id: number; role: 'user'; text: string }
  | {
      id: number
      role: 'assistant'
      status: 'answered' | 'no_sources'
      text: string
      sources: AskSource[]
      generalKnowledge: boolean
      actions: AskAction[]
      checked: string[]
    }
  | {
      id: number
      role: 'error'
      kind: 'rate_limited' | 'failed'
      text: string
      question: string
    }

const HISTORY_TURNS = 6 // the server keeps the last 6 turns anyway
const FAILED = "The AI service didn't respond. Your question is kept, so you can try again."

function toError(error: unknown, question: string, id: number): ChatMessage {
  if (error instanceof ApiError && error.status === 429) {
    return { id, role: 'error', kind: 'rate_limited', text: error.message, question }
  }
  if (error instanceof ApiError && error.status === 401) {
    const text = 'Your session has expired. Please sign in again.'
    return { id, role: 'error', kind: 'failed', text, question }
  }
  return { id, role: 'error', kind: 'failed', text: FAILED, question }
}

/** The questions and answers so far, so follow-ups like "explain that" work. */
function historyOf(messages: ChatMessage[]): HistoryTurn[] {
  const turns: HistoryTurn[] = []
  for (const m of messages) {
    if (m.role === 'user') turns.push({ role: 'user', content: m.text })
    if (m.role === 'assistant') turns.push({ role: 'assistant', content: m.text })
  }
  return turns.slice(-HISTORY_TURNS)
}

/** The conversation lives here, in memory only: it is gone on reload or sign-out. */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const nextId = useRef(0)
  const generation = useRef(0) // bumped by "New chat", so late answers are ignored
  const { mutate, isPending, reset: resetMutation } = useMutation({ mutationFn: askQuestion })

  const ask = useCallback(
    (question: string, history: HistoryTurn[], showQuestion: boolean) => {
      const gen = generation.current
      if (showQuestion) {
        const id = nextId.current++
        setMessages((m) => [...m, { id, role: 'user', text: question }])
      }
      mutate(
        { question, history },
        {
          onSuccess: (res) => {
            if (gen !== generation.current) return
            const id = nextId.current++
            setMessages((m) => [
              ...m,
              {
                id,
                role: 'assistant',
                status: res.status,
                text: res.answer,
                sources: res.sources,
                generalKnowledge: res.general_knowledge,
                actions: res.actions,
                checked: res.checked,
              },
            ])
          },
          onError: (error) => {
            if (gen !== generation.current) return
            const id = nextId.current++
            setMessages((m) => [...m, toError(error, question, id)])
          },
        },
      )
    },
    [mutate],
  )

  const send = useCallback(
    (text: string) => {
      const question = text.trim()
      if (!question || isPending) return
      ask(question, historyOf(messages), true)
    },
    [ask, isPending, messages],
  )

  const retry = useCallback(
    (errorId: number) => {
      const at = messages.findIndex((m) => m.id === errorId)
      const failed = messages[at]
      if (!failed || failed.role !== 'error' || isPending) return
      // Everything before the failed question is the history for this retry.
      const before = messages.slice(0, at)
      const last = before.at(-1)
      const earlier = last?.role === 'user' ? before.slice(0, -1) : before
      setMessages((m) => m.filter((x) => x.id !== errorId))
      ask(failed.question, historyOf(earlier), false)
    },
    [ask, isPending, messages],
  )

  const reset = useCallback(() => {
    generation.current++
    setMessages([])
    resetMutation()
  }, [resetMutation])

  return { messages, pending: isPending, send, retry, reset }
}
