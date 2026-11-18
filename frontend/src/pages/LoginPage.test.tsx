import { fireEvent, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'

import { LoginPage } from '@/pages/LoginPage'
import { renderRoutes } from '@/test/renderRoutes'
import { server } from '@/test/server'

const viewer = { id: 'u-1', email: 'ana@demo.exin', full_name: 'Ana Test', role: 'viewer' }

const routes = [
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <p>Home page</p> },
  { path: '/documents/:id', element: <p>Document page</p> },
]

async function signIn(email: string, password: string) {
  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    server.use(
      http.get('/api/auth/me', () =>
        HttpResponse.json({ detail: 'Not authenticated.' }, { status: 401 }),
      ),
    )
  })

  it('shows the API error on a wrong password', async () => {
    server.use(
      http.post('/api/auth/login', () =>
        HttpResponse.json({ detail: 'Incorrect email or password.' }, { status: 401 }),
      ),
    )
    renderRoutes(routes, ['/login'])

    await signIn('ana@demo.exin', 'wrong')

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.')
  })

  it('returns to the page the user wanted after signing in', async () => {
    server.use(http.post('/api/auth/login', () => HttpResponse.json({ user: viewer })))
    renderRoutes(routes, [{ pathname: '/login', state: { from: '/documents/7' } }])

    await signIn('ana@demo.exin', 'correct-horse-battery')

    expect(await screen.findByText('Document page')).toBeInTheDocument()
  })

  it('ignores redirects to other sites', async () => {
    server.use(http.post('/api/auth/login', () => HttpResponse.json({ user: viewer })))
    renderRoutes(routes, [{ pathname: '/login', state: { from: '//evil.example' } }])

    await signIn('ana@demo.exin', 'correct-horse-battery')

    expect(await screen.findByText('Home page')).toBeInTheDocument()
  })

  it('skips the form when already signed in', async () => {
    server.use(http.get('/api/auth/me', () => HttpResponse.json(viewer)))
    renderRoutes(routes, ['/login'])

    expect(await screen.findByText('Home page')).toBeInTheDocument()
  })
})
