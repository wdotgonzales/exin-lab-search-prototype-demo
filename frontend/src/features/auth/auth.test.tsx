import { fireEvent, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'

import { RequireAuth } from '@/components/layout/RequireAuth'
import { UserMenu } from '@/components/layout/UserMenu'
import { useLogout } from '@/features/auth/useAuth'
import { renderRoutes } from '@/test/renderRoutes'
import { server } from '@/test/server'

const viewer = { id: 'u-1', email: 'ana@demo.exin', full_name: 'Ana Test', role: 'viewer' }

const signedIn = () =>
  server.use(http.get('/api/auth/me', () => HttpResponse.json(viewer)))

const signedOut = () =>
  server.use(
    http.get('/api/auth/me', () =>
      HttpResponse.json({ detail: 'Not authenticated.' }, { status: 401 }),
    ),
  )

function LoginProbe() {
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  return <p>{`Login page, from: ${from ?? 'none'}`}</p>
}

function SignOutButton() {
  const logout = useLogout()
  return <button onClick={() => logout.mutate()}>Sign out</button>
}

const protectedRoutes = (page: ReactNode) => [
  { path: '/login', element: <LoginProbe /> },
  { element: <RequireAuth />, children: [{ path: '*', element: page }] },
]

describe('RequireAuth', () => {
  it('sends signed-out visitors to /login and remembers where they were going', async () => {
    signedOut()
    renderRoutes(protectedRoutes(<p>Secret</p>), ['/documents/7?tab=notes'])

    expect(
      await screen.findByText('Login page, from: /documents/7?tab=notes'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Secret')).not.toBeInTheDocument()
  })

  it('shows the page when signed in', async () => {
    signedIn()
    renderRoutes(protectedRoutes(<p>Secret</p>))

    expect(await screen.findByText('Secret')).toBeInTheDocument()
  })

  it('offers a retry when the API is unreachable', async () => {
    server.use(http.get('/api/auth/me', () => new HttpResponse(null, { status: 502 })))
    renderRoutes(protectedRoutes(<p>Secret</p>))

    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})

describe('signing out', () => {
  it('returns to /login without a reload', async () => {
    signedIn()
    server.use(http.post('/api/auth/logout', () => new HttpResponse(null, { status: 204 })))
    renderRoutes(protectedRoutes(<SignOutButton />))

    fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

    expect(await screen.findByText(/^Login page/)).toBeInTheDocument()
  })
})

describe('UserMenu', () => {
  it('shows who is signed in', async () => {
    signedIn()
    renderRoutes([{ path: '/', element: <UserMenu /> }])

    expect(await screen.findByRole('button', { name: /Ana Test/ })).toBeInTheDocument()
    expect(screen.getByText('AT')).toBeInTheDocument()
  })
})
