import { createBrowserRouter, Navigate } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'
import { RequireAuth } from '@/components/layout/RequireAuth'
import { ActivityPage } from '@/pages/ActivityPage'
import { DocumentPage } from '@/pages/DocumentPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/documents" replace /> },
      { path: 'documents', element: <DocumentsPage /> },
      { path: 'documents/:id', element: <DocumentPage /> },
      { path: 'activity', element: <ActivityPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
