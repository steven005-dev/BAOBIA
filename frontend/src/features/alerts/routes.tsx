/**
 * Routes du module alertes (responsable : Yéo).
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import type { RouteObject } from 'react-router'

import { AlertDetailPage } from './AlertDetailPage'
import { AlertsPage } from './AlertsPage'

export const alertsRoutes: RouteObject[] = [
  { path: 'alertes', element: <AlertsPage /> },
  { path: 'alertes/:alertId', element: <AlertDetailPage /> },
]
