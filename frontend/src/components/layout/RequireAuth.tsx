import type { ReactNode } from 'react'

// TODO(auth): call /api/auth/me; redirect to /login when it returns 401.
export function RequireAuth({ children }: { children: ReactNode }) {
  return <>{children}</>
}
