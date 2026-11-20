/**
 * Routes du module santé (responsable : Yéo) : signalements, évaluation vétérinaire.
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import type { RouteObject } from 'react-router'

import { ReportDetailPage } from './ReportDetailPage'
import { ReportPage } from './ReportPage'
import { ReportsPage } from './ReportsPage'

export const healthRoutes: RouteObject[] = [
  { path: 'sante', element: <ReportsPage /> },
  { path: 'sante/signaler', element: <ReportPage /> },
  { path: 'sante/:reportId', element: <ReportDetailPage /> },
]
