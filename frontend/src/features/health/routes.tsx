/**
 * Routes du module santé (responsable : Yéo) : signalements, évaluation vétérinaire.
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import { HeartPulse } from 'lucide-react'
import type { RouteObject } from 'react-router'

import { ModulePlaceholder } from '@/app/ModulePlaceholder'
import { mots } from '@/lib/vocabulaire'

export const healthRoutes: RouteObject[] = [
  { path: 'sante', element: <ModulePlaceholder title={mots.sante} icon={HeartPulse} /> },
]
