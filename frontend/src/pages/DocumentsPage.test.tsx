import { fireEvent, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import type { DocumentItem } from '@/features/documents/useDocuments'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { renderRoutes } from '@/test/renderRoutes'
import { server } from '@/test/server'

const doc = (over: Partial<DocumentItem>): DocumentItem => ({
  id: crypto.randomUUID(),
  title: 'C-07 surgery log',
  filename: 'C-07_surgery_log.csv',
  file_type: 'csv',
  size_bytes: 48_000,
  status: 'pending',
  error_message: null,
  uploaded_by_name: 'Demo Admin',
  created_at: '2026-11-18T05:56:00Z',
  ...over,
})

const DOCS = [
  doc({ title: 'C-07 surgery log', status: 'pending' }),
  doc({ title: 'V-017 virus QC report', filename: 'V-017_QC.pdf', status: 'indexed' }),
  doc({ title: 'Old freezer scan', filename: 'freezer.pdf', status: 'failed', error_message: 'No text found' }),
]

let lastUrl: URL

function serve(role: 'admin' | 'viewer', all: DocumentItem[] = DOCS, total?: number) {
  server.use(
    http.get('/api/auth/me', () =>
      HttpResponse.json({ id: 'u-1', email: 'a@demo.exin', full_name: 'Ana Test', role }),
    ),
    http.get('/api/documents', ({ request }) => {
      lastUrl = new URL(request.url)
      const q = (lastUrl.searchParams.get('q') ?? '').toLowerCase()
      const offset = Number(lastUrl.searchParams.get('offset') ?? 0)
      const matches = all.filter((d) => d.title.toLowerCase().includes(q))
      return HttpResponse.json({ items: matches.slice(offset, offset + 20), total: total ?? matches.length })
    }),
  )
}

const renderPage = () => renderRoutes([{ path: '/documents', element: <DocumentsPage /> }], ['/documents'])

describe('DocumentsPage', () => {
  it('lists documents with friendly status labels', async () => {
    serve('viewer')
    renderPage()

    expect(await screen.findByText('V-017 virus QC report')).toBeInTheDocument()
    expect(screen.getByText('Waiting to index')).toBeInTheDocument()
    expect(screen.getByText('Searchable')).toBeInTheDocument()
    expect(screen.getByText("Can't read file")).toBeInTheDocument()
    expect(screen.getByText('3 files')).toBeInTheDocument()
  })

  it('filters by name through the API', async () => {
    serve('viewer')
    renderPage()
    await screen.findByText('C-07 surgery log')

    fireEvent.change(screen.getByLabelText('Filter documents by title or filename'), {
      target: { value: 'surgery' },
    })

    await waitFor(() => expect(lastUrl.searchParams.get('q')).toBe('surgery'))
    await waitFor(() => expect(screen.queryByText('V-017 virus QC report')).not.toBeInTheDocument())
  })

  it('offers to clear a filter with no matches', async () => {
    serve('viewer')
    renderPage()
    await screen.findByText('C-07 surgery log')

    fireEvent.change(screen.getByLabelText('Filter documents by title or filename'), {
      target: { value: 'zzz' },
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Clear filter' }))

    expect(await screen.findByText('C-07 surgery log')).toBeInTheDocument()
  })

  it('pages through results', async () => {
    const many = Array.from({ length: 25 }, (_, i) => doc({ title: `Doc ${i + 1}` }))
    serve('viewer', many)
    renderPage()
    expect(await screen.findByText('Showing 1–20 of 25')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    await waitFor(() => expect(lastUrl.searchParams.get('offset')).toBe('20'))
    expect(await screen.findByText('Showing 21–25 of 25')).toBeInTheDocument()
  })

  it('shows the upload button to admins only', async () => {
    serve('viewer')
    const { unmount } = renderPage()
    await screen.findByText('C-07 surgery log')
    expect(screen.queryByRole('button', { name: /upload files/i })).not.toBeInTheDocument()
    unmount()

    serve('admin')
    renderPage()
    expect(await screen.findByRole('button', { name: /upload files/i })).toBeInTheDocument()
  })
  it('explains a failed file in its tooltip', async () => {
    serve('viewer')
    renderPage()

    fireEvent.focus(await screen.findByRole('button', { name: "Can't read file" }))

    expect(await screen.findByRole('tooltip')).toHaveTextContent('No text found')
  })

  it('explains every status in the legend', async () => {
    serve('viewer')
    renderPage()
    await screen.findByText('C-07 surgery log')

    fireEvent.click(screen.getByRole('button', { name: 'What do the search statuses mean?' }))

    expect(await screen.findByText('The assistant can find and cite this file.')).toBeInTheDocument()
    expect(screen.getByText(/Uploading only stores the file/)).toBeInTheDocument()
  })
})
