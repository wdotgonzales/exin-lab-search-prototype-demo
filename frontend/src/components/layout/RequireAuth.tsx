import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { Button } from '@/components/ui/button'
import { useMe } from '@/features/auth/useAuth'

function FullPage({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background p-6 text-center text-sm text-muted-foreground">
      {children}
    </div>
  )
}

export function RequireAuth({ children }: { children?: ReactNode }) {
  const location = useLocation()
  const { data: user, isPending, isError, refetch, isRefetching } = useMe()

  if (isPending) {
    return (
      <FullPage>
        <span className="animate-pulse">Loading…</span>
      </FullPage>
    )
  }

  if (isError) {
    return (
      <FullPage>
        <p>We couldn't reach the server. Check your connection and try again.</p>
        <Button variant="outline" onClick={() => refetch()} disabled={isRefetching}>
          {isRefetching ? 'Retrying…' : 'Retry'}
        </Button>
      </FullPage>
    )
  }

  if (!user) {
    const from = location.pathname + location.search + location.hash
    return <Navigate to="/login" replace state={{ from }} />
  }

  return children ?? <Outlet />
}
