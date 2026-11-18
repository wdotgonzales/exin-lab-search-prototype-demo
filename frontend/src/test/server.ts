import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

export const handlers = [
  http.get('/api/health', () =>
    HttpResponse.json({ status: 'ok', database: 'ok', pgvector: '0.8.7' }),
  ),
]

export const server = setupServer(...handlers)
