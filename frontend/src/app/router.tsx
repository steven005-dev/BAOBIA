/**
 * Routage de l'application. Chaque module déclare ses routes dans
 * src/features/<module>/routes.tsx : ce fichier ne fait que les assembler.
 */

import { CircleHelp } from 'lucide-react'
import { createBrowserRouter, type RouteObject } from 'react-router'

import { LoginPage } from '@/auth/LoginPage'
import { RequireAuth } from '@/auth/RequireAuth'
import { EmptyState } from '@/components/EmptyState'
import { alertsRoutes } from '@/features/alerts/routes'
import { healthRoutes } from '@/features/health/routes'
import { identityRoutes } from '@/features/identity/routes'
import { mapRoutes } from '@/features/map/routes'
import { movementsRoutes } from '@/features/movements/routes'
import { messages } from '@/lib/vocabulaire'

import { AppLayout } from './AppLayout'
import { HomePage } from './HomePage'

// Page de démonstration des composants : en développement seulement (absente du build).
const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [{ path: '/composants', lazy: async () => ({ Component: (await import('@/dev/ComponentsPage')).default }) }]
  : []

export const router = createBrowserRouter([
  { path: '/connexion', element: <LoginPage /> },
  ...devRoutes,
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <HomePage /> },
      ...identityRoutes,
      ...movementsRoutes,
      ...healthRoutes,
      ...alertsRoutes,
      ...mapRoutes,
      { path: '*', element: <EmptyState icon={CircleHelp} title={messages.pageIntrouvable} /> },
    ],
  },
])
