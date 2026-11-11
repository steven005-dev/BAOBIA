/**
 * Routes du module carte (responsable : Yéo). Réutiliser HEALTH_STATES
 * (src/lib/healthStates.ts) pour la légende et les zones.
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import { Map as MapIcon } from 'lucide-react'
import type { RouteObject } from 'react-router'

import { ModulePlaceholder } from '@/app/ModulePlaceholder'
import { mots } from '@/lib/vocabulaire'

export const mapRoutes: RouteObject[] = [
  { path: 'carte', element: <ModulePlaceholder title={mots.carte} icon={MapIcon} /> },
]
