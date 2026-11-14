/**
 * Routes du module identity (responsable : chef de projet) : élevages, animaux, scan.
 * Ne pas modifier src/app/ : le routeur assemble ces routes.
 */

import type { RouteObject } from 'react-router'

import { AddUnitPage } from './AddUnitPage'
import { AnimalsPage } from './AnimalsPage'
import { ScanPage } from './ScanPage'
import { UnitPage } from './UnitPage'

export const identityRoutes: RouteObject[] = [
  { path: 'centres', element: <AnimalsPage /> },
  { path: 'centres/:centerId/ajouter', element: <AddUnitPage /> },
  { path: 'centres/animaux/:unitId', element: <UnitPage /> },
  { path: 'scanner', element: <ScanPage /> },
]
