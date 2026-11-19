import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router'

import { Logo } from '@/components/layout/Logo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLogin, useMe } from '@/features/auth/useAuth'
import { ApiError } from '@/lib/api'

/** Only allow internal paths, never "//evil.com" or back to /login. */
function safeRedirect(from: unknown): string {
  if (
    typeof from === 'string' &&
    from.startsWith('/') &&
    !from.startsWith('//') &&
    !from.startsWith('/login')
  ) {
    return from
  }
  return '/'
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status < 500) return error.message
  return "Couldn't reach the server. Try again in a moment."
}

export function LoginPage() {
  const location = useLocation()
  const redirectTo = safeRedirect((location.state as { from?: unknown } | null)?.from)

  const me = useMe()
  const login = useLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  if (me.data) return <Navigate to={redirectTo} replace />

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate({ email: email.trim(), password })
  }

  return (
    <div className="grid min-h-svh bg-background lg:grid-cols-2">
      {/* Brand panel: desktop only */}
      <aside className="hidden flex-col justify-between border-r border-border bg-card p-10 lg:flex">
        <Logo />
        <div className="space-y-6">
          <h1 className="font-serif text-5xl leading-tight text-foreground">
            Exin Therapeutics{' '}
            <span className="text-primary">Document Repository</span>
          </h1>
          <p className="max-w-md text-muted-foreground">
            Upload, search and read the lab&apos;s documents.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">Prototype · demo data only</p>
      </aside>

      {/* Form: every screen size */}
      <main className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden">
            <Logo />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-semibold text-foreground">Sign in</h2>
            <p className="text-sm text-muted-foreground">
              Use the account your lab admin created for you.
            </p>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                autoFocus
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {login.isError && (
              <p role="alert" className="text-sm text-destructive">
                {errorMessage(login.error)}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={login.isPending}>
              {login.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </div>
      </main>
    </div>
  )
}
