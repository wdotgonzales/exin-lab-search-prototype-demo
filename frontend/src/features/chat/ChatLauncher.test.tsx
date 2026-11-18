import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'

import { server } from '@/test/server'

import type { AskResponse } from './api'
import { ChatLauncher } from './ChatLauncher'

const ANSWER: AskResponse = {
  status: 'answered',
  answer: 'That was M-045. Its window clouded [1].',
  sources: [
    {
      n: 1,
      document_id: 'a30a6044-160a-45b5-bc5b-a71ac1c0fc01',
      title: 'incident 2026-10-14 M-045 window',
      filename: 'incident_2026-10-14_M-045_window.md',
      snippet: '…the window over left mPFC was cloudy…',
      page_number: null,
    },
  ],
}

function Where() {
  const location = useLocation()
  return <p>at {location.pathname + location.search}</p>
}

function renderChat() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<ChatLauncher />} />
          <Route path="/documents" element={<Where />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Open lab assistant' }))
}

function ask(question: string) {
  const box = screen.getByLabelText('Ask the lab assistant')
  fireEvent.change(box, { target: { value: question } })
  fireEvent.keyDown(box, { key: 'Enter' })
}

describe('ChatLauncher', () => {
  it('opens on an empty chat with example questions', () => {
    renderChat()
    expect(screen.getByRole('heading', { name: "Ask about the lab's documents" })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'What virus batch was used in EXP-007?' }),
    ).toBeInTheDocument()
  })

  it('shows the question, then the answer with its source card', async () => {
    server.use(http.post('/api/ask', () => HttpResponse.json(ANSWER)))
    renderChat()

    ask('What happened to M-045?')

    expect(screen.getByText('What happened to M-045?')).toBeInTheDocument()
    expect(await screen.findByText(/Its window clouded/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show source 1' })).toBeInTheDocument()
    const card = screen.getByRole('article', { name: 'Source 1' })
    expect(within(card).getByText('incident 2026-10-14 M-045 window')).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: /Open/ })).toHaveAttribute(
      'href',
      '/api/documents/a30a6044-160a-45b5-bc5b-a71ac1c0fc01/file',
    )
  })

  it('"Show in list" opens Documents filtered to that file', async () => {
    server.use(http.post('/api/ask', () => HttpResponse.json(ANSWER)))
    renderChat()
    ask('What happened to M-045?')

    fireEvent.click(await screen.findByRole('button', { name: /Show in list/ }))

    expect(
      await screen.findByText('at /documents?q=incident_2026-10-14_M-045_window.md'),
    ).toBeInTheDocument()
  })

  it('says so when nothing was found', async () => {
    server.use(
      http.post('/api/ask', () =>
        HttpResponse.json({
          status: 'no_sources',
          answer: "I couldn't find this in the uploaded documents.",
          sources: [],
        }),
      ),
    )
    renderChat()
    ask('What was the weather in Paris?')

    expect(
      await screen.findByText("I couldn't find this in the uploaded documents."),
    ).toBeInTheDocument()
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it('shows the server message when the hourly limit is reached', async () => {
    server.use(
      http.post('/api/ask', () =>
        HttpResponse.json(
          { detail: "You've reached 20 questions this hour. You can ask again in 12 minutes." },
          { status: 429 },
        ),
      ),
    )
    renderChat()
    ask('one more?')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('You can ask again in 12 minutes.')
  })

  it('offers "Try again" after a failure, without repeating the question', async () => {
    let calls = 0
    server.use(
      http.post('/api/ask', () =>
        calls++ === 0
          ? HttpResponse.json({ detail: 'upstream failed' }, { status: 502 })
          : HttpResponse.json(ANSWER),
      ),
    )
    renderChat()
    ask('What happened to M-045?')

    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))

    expect(await screen.findByText(/Its window clouded/)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getAllByText('What happened to M-045?')).toHaveLength(1)
  })

  it('"New chat" clears the conversation', async () => {
    server.use(http.post('/api/ask', () => HttpResponse.json(ANSWER)))
    renderChat()
    ask('What happened to M-045?')
    await screen.findByText(/Its window clouded/)

    fireEvent.click(screen.getByRole('button', { name: 'New chat' }))

    expect(screen.getByRole('heading', { name: "Ask about the lab's documents" })).toBeInTheDocument()
    expect(screen.queryByText('What happened to M-045?')).not.toBeInTheDocument()
  })
})
