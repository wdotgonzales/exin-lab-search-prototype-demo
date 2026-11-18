import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { HomePage } from './HomePage'
import { renderWithProviders } from '@/test/render'
import { server } from '@/test/server'

describe('HomePage', () => {
  it('shows the API status when the backend is healthy', async () => {
    renderWithProviders(<HomePage />)

    expect(await screen.findByText('API ok · pgvector 0.8.7')).toBeInTheDocument()
  })

  it('shows an error when the backend is down', async () => {
    server.use(
      http.get('/api/health', () =>
        HttpResponse.json({ detail: 'Service unavailable' }, { status: 503 }),
      ),
    )

    renderWithProviders(<HomePage />)

    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument()
  })
})
