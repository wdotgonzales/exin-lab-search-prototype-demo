import { useMutation } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'

import { ApiError } from '@/lib/api'

import { askQuestion, type AskSource } from './api'

export type ChatMessage =
  | { id: number; role: 'user'; text: string }
  | {
      id: number
      role: 'assistant'
      status: 'answered' | 'no_sources'
      text: string
      sources: AskSource[]
    }
  | {
      id: number
      role: 'error'
      kind: 'rate_limited' | 'failed'
      text: string
      question: string
    }

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

/** The conversation lives here, in memory only: it is gone on reload or sign-out. */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const nextId = useRef(0)
  const generation = useRef(0) // bumped by "New chat", so late answers are ignored
  const { mutate, isPending, reset: resetMutation } = useMutation({ mutationFn: askQuestion })

  const ask = useCallback(
    (question: string, showQuestion: boolean) => {
      const gen = generation.current
      if (showQuestion) {
        const id = nextId.current++
        setMessages((m) => [...m, { id, role: 'user', text: question }])
      }
      mutate(question, {
        onSuccess: (res) => {
          if (gen !== generation.current) return
          const id = nextId.current++
          setMessages((m) => [
            ...m,
            { id, role: 'assistant', status: res.status, text: res.answer, sources: res.sources },
          ])
        },
        onError: (error) => {
          if (gen !== generation.current) return
          const id = nextId.current++
          setMessages((m) => [...m, toError(error, question, id)])
        },
      })
    },
    [mutate],
  )

  const send = useCallback(
    (text: string) => {
      const question = text.trim()
      if (!question || isPending) return
      ask(question, true)
    },
    [ask, isPending],
  )

  const retry = useCallback(
    (errorId: number) => {
      const failed = messages.find((m) => m.id === errorId)
      if (!failed || failed.role !== 'error' || isPending) return
      setMessages((m) => m.filter((x) => x.id !== errorId))
      ask(failed.question, false)
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
