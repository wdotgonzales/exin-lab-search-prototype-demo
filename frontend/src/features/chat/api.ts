import { api } from '@/lib/api'

export type AskSource = {
  n: number
  document_id: string
  title: string
  filename: string
  snippet: string
  page_number: number | null
}

export type AskResponse = {
  status: 'answered' | 'no_sources'
  answer: string
  sources: AskSource[]
}

export function askQuestion(question: string) {
  return api<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}
