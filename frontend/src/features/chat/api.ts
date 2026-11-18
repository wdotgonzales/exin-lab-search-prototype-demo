import { api } from '@/lib/api'

export type AskSource = {
  n: number
  document_id: string
  title: string
  filename: string
  snippet: string
  page_number: number | null
}

export type AskAction =
  | { type: 'open_document'; label: string; document_id: string; query: null }
  | { type: 'show_in_list'; label: string; document_id: null; query: string }

export type AskResponse = {
  status: 'answered' | 'no_sources'
  answer: string
  sources: AskSource[]
  general_knowledge: boolean
  actions: AskAction[]
  checked: string[]
}

export type HistoryTurn = { role: 'user' | 'assistant'; content: string }

export function askQuestion({ question, history }: { question: string; history: HistoryTurn[] }) {
  return api<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ question, history }),
  })
}
