/**
 * Routes du module carte (responsable : Yéo). La légende et les zones réutilisent
 * HEALTH_STATES (src/lib/healthStates.ts).
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import type { RouteObject } from 'react-router'

import { MapPage } from './MapPage'

export const mapRoutes: RouteObject[] = [{ path: 'carte', element: <MapPage /> }]
