import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { api, ApiError } from './api'
import { server } from '@/test/server'

describe('api', () => {
  it('returns parsed JSON on success', async () => {
    await expect(api('/health')).resolves.toMatchObject({ status: 'ok' })
  })

  it('throws ApiError with the FastAPI detail message', async () => {
    server.use(
      http.get('/api/health', () =>
        HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 }),
      ),
    )

    const request = api('/health')

    await expect(request).rejects.toBeInstanceOf(ApiError)
    await expect(request).rejects.toMatchObject({ status: 401, message: 'Not authenticated' })
  })

  it('handles an empty error body', async () => {
    server.use(http.get('/api/health', () => new HttpResponse(null, { status: 502 })))

    await expect(api('/health')).rejects.toMatchObject({ message: 'Request failed (502)' })
  })
})
