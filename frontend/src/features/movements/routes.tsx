/**
 * Routes du module mouvements (responsable : Konan Romuald).
 * Ajouter ici les écrans (Transférer, Recevoir, Confirmer...) ; ne pas modifier src/app/.
 * Exemple : { path: 'mouvements/recevoir', element: <ReceptionPage /> }
 */

import { ArrowLeftRight } from 'lucide-react'
import type { RouteObject } from 'react-router'

import { ModulePlaceholder } from '@/app/ModulePlaceholder'
import { mots } from '@/lib/vocabulaire'

export const movementsRoutes: RouteObject[] = [
  { path: 'mouvements', element: <ModulePlaceholder title={mots.mouvements} icon={ArrowLeftRight} /> },
]
