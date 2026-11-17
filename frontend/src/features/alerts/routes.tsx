/**
 * Routes du module alertes (responsable : Yéo).
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import { Siren } from 'lucide-react'
import type { RouteObject } from 'react-router'

import { ModulePlaceholder } from '@/app/ModulePlaceholder'
import { mots } from '@/lib/vocabulaire'

export const alertsRoutes: RouteObject[] = [
  { path: 'alertes', element: <ModulePlaceholder title={mots.alertes} icon={Siren} /> },
]
