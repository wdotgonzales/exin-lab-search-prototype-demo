import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import type { DocumentDetail } from '@/features/documents/useDocument'
import { DocumentPage } from '@/pages/DocumentPage'
import { renderRoutes } from '@/test/renderRoutes'
import { server } from '@/test/server'

// jsdom can't draw Word files: check that the DOCX viewer is handed the file instead
const renderAsync = vi.fn().mockResolvedValue(undefined)
vi.mock('docx-preview', () => ({ renderAsync: (...args: unknown[]) => renderAsync(...args) }))

const ID = '11111111-2222-3333-4444-555555555555'

const detail = (over: Partial<DocumentDetail> = {}): DocumentDetail => ({
  id: ID,
  title: 'EXP-007 interim report',
  filename: 'EXP-007_interim_report.pdf',
  file_type: 'pdf',
  size_bytes: 3_000,
  status: 'indexed',
  error_message: null,
  uploaded_by_name: 'Demo Admin',
  created_at: '2026-11-18T05:56:00Z',
  summary: 'XN-214 cut event rates by about 31%.',
  indexed_at: '2026-11-19T05:13:00Z',
  passage_count: 3,
  lab_ids: [],
  ...over,
})

function serve(
  doc: DocumentDetail | 404 | 422,
  role: 'admin' | 'viewer' = 'admin',
  content = '',
) {
  server.use(
    http.get('/api/auth/me', () =>
      HttpResponse.json({ id: 'u-1', email: 'a@demo.exin', full_name: 'Ana Test', role }),
    ),
    http.get('/api/documents/:id', () =>
      typeof doc === 'number'
        ? HttpResponse.json({ detail: 'Document not found.' }, { status: doc })
        : HttpResponse.json(doc),
    ),
    http.get('/api/documents/:id/text', () =>
      HttpResponse.json({
        sections: [{ label: null, page: 1, text: 'Extracted hello' }],
        truncated: false,
      }),
    ),
    http.get('/api/documents/:id/content', () => HttpResponse.text(content)),
    http.get('/api/documents/:id/table', () =>
      HttpResponse.json({
        sheets: [{ name: 'Scores', rows: [['Mouse', 'Index'], ['M-013', '0.33']], truncated: false }],
      }),
    ),
  )
}

const renderPage = (id = ID) =>
  renderRoutes(
    [
      { path: '/documents/:id', element: <DocumentPage /> },
      { path: '/documents', element: <p>List page</p> },
    ],
    [`/documents/${id}`],
  )

// Radix menus open on pointerdown, others on click: try both.
async function openMenu() {
  const trigger = await screen.findByRole('button', { name: /more actions/i })
  fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false, pointerType: 'mouse' })
  if (screen.queryAllByRole('menuitem').length === 0) fireEvent.click(trigger)
  await screen.findAllByRole('menuitem')
}

describe('DocumentPage', () => {
  it('shows the title, summary and details', async () => {
    serve(detail())
    renderPage()

    expect(await screen.findByRole('heading', { name: 'EXP-007 interim report' })).toBeInTheDocument()
    expect(screen.getByText('XN-214 cut event rates by about 31%.')).toBeInTheDocument()
    expect(screen.getByText(/3 passages/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open original/i })).toHaveAttribute(
      'href',
      `/api/documents/${ID}/file`,
    )
  })

  it.each([404, 422] as const)('shows "not found" for a %s', async (status) => {
    serve(status)
    renderPage('not-a-real-id')
    expect(await screen.findByText('Document not found')).toBeInTheDocument()
  })

  it('previews a PDF in the browser viewer and switches to extracted text', async () => {
    serve(detail())
    renderPage()

    expect(await screen.findByTitle(/PDF preview/)).toHaveAttribute(
      'src',
      `/api/documents/${ID}/content`,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Extracted text' }))
    expect(await screen.findByText('Extracted hello')).toBeInTheDocument()
    expect(screen.queryByTitle(/PDF preview/)).not.toBeInTheDocument()
  })

  it('renders Markdown as formatted text', async () => {
    serve(detail({ file_type: 'md', filename: 'notes.md' }), 'admin', '# Incident\n\n- M-045 excluded')
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Incident' })).toBeInTheDocument()
    expect(screen.getByRole('listitem')).toHaveTextContent('M-045 excluded')
  })

  it('shows plain text as-is', async () => {
    serve(detail({ file_type: 'txt', filename: 'log.txt' }), 'admin', '2026-10-13  M-045  aborted')
    renderPage()
    // keep the exact spacing: the viewer must not collapse it
    expect(
      await screen.findByText('2026-10-13  M-045  aborted', { normalizer: (s) => s }),
    ).toBeInTheDocument()
  })

  it('shows spreadsheets as a table', async () => {
    serve(detail({ file_type: 'xlsx', filename: 'scores.xlsx' }))
    renderPage()
    expect(await screen.findByRole('columnheader', { name: 'Mouse' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'M-013' })).toBeInTheDocument()
  })

  it('hands Word files to the DOCX viewer', async () => {
    renderAsync.mockClear()
    serve(detail({ file_type: 'docx', filename: 'notes.docx' }), 'admin', 'fake docx bytes')
    renderPage()
    await waitFor(() => expect(renderAsync).toHaveBeenCalled())
    expect(renderAsync.mock.calls[0][0]).toBeInstanceOf(ArrayBuffer)
  })

  it('lets viewers download and copy the link, but not delete', async () => {
    serve(detail(), 'viewer')
    renderPage()
    await openMenu()
    expect(screen.getByRole('menuitem', { name: /download/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /copy link/i })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: /delete/i })).not.toBeInTheDocument()
  })

  it('lets admins delete the file and returns to the list', async () => {
    let sent: string[] = []
    serve(detail())
    server.use(
      http.post('/api/documents/delete', async ({ request }) => {
        sent = ((await request.json()) as { document_ids: string[] }).document_ids
        return HttpResponse.json({ deleted: sent, not_found: [] })
      }),
    )
    renderPage()

    await openMenu()
    fireEvent.click(screen.getByRole('menuitem', { name: /delete file/i }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('EXP-007_interim_report.pdf')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Yes, delete' }))

    expect(await screen.findByText('List page')).toBeInTheDocument()
    expect(sent).toEqual([ID])
  })
})
