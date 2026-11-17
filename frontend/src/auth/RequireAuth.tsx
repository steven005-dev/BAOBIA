/**
 * Route protégée : sans session, renvoie vers /connexion (puis revient à la page
 * demandée après connexion).
 *
 * Exemple (déjà fait dans src/app/router.tsx) :
 *   { element: <RequireAuth><AppLayout /></RequireAuth>, children: [...] }
 */

import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { Loader } from '@/components/Loader'

import { useAuth } from './AuthProvider'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <Loader fullPage />
  if (status === 'anonymous') {
    return <Navigate to="/connexion" replace state={{ from: location.pathname + location.search }} />
  }
  return children
}
