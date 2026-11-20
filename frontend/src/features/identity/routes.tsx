/**
 * Routes du module identity (responsable : chef de projet) : élevages, animaux, scan.
 * Ne pas modifier src/app/ : le routeur assemble ces routes.
 */

import type { RouteObject } from 'react-router'

import { AddCenterPage } from './AddCenterPage'
import { AddUnitPage } from './AddUnitPage'
import { AnimalsPage } from './AnimalsPage'
import { IssueLabelsPage } from './IssueLabelsPage'
import { RegisterBreederPage } from './RegisterBreederPage'
import { ReplaceLabelPage } from './ReplaceLabelPage'
import { ScanPage } from './ScanPage'
import { UnitPage } from './UnitPage'

export const identityRoutes: RouteObject[] = [
  { path: 'centres', element: <AnimalsPage /> },
  { path: 'centres/nouveau', element: <AddCenterPage /> },
  { path: 'etiquettes', element: <IssueLabelsPage /> },
  { path: 'eleveurs/nouveau', element: <RegisterBreederPage /> },
  { path: 'centres/:centerId/ajouter', element: <AddUnitPage /> },
  { path: 'centres/animaux/:unitId', element: <UnitPage /> },
  { path: 'centres/animaux/:unitId/etiquette', element: <ReplaceLabelPage /> },
  { path: 'scanner', element: <ScanPage /> },
]
